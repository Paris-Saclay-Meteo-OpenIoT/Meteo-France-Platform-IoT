const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { findUser, updateUserPassword, findUserById } = require('../model/userModel');
const { sendResetPasswordEmail, sendPasswordChangeConfirmationEmail } = require('../config/mailer');

// fonction pour gérer la demande de réinitialisation de mot de passe
async function forgotPassword(req, res) {
  const { email } = req.body;
  if (!email) return res.status(400).json({ error: 'Email requis' });
    
  const user = await findUser(email);
  if (!user) {
    return res.status(200).json({ message: "Si cet email est associé à un compte, un lien de réinitialisation vous a été envoyé." });
  }
  
  const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: '1h' });

  // Utiliser la variable d'environnement ENVIRONMENT_URL
  const baseUrl = process.env.ENVIRONMENT_URL || 'http://localhost:5000';
  const resetLink = `${baseUrl}reset-password?token=${token}`;  

  await sendResetPasswordEmail(email, resetLink);

  res.status(200).json({ message: "Si cet email est associé à un compte, un lien de réinitialisation vous a été envoyé." });
}

// fonction pour gérer la réinitialisation de mot de passe
async function resetPassword(req, res) {
  const { token, newPassword } = req.body;
  if (!token || !newPassword) return res.status(400).json({ error: 'Token et nouveau mot de passe requis' });

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const userId = decoded.id;

    const saltRounds = 10;
    const hashedPassword = await bcrypt.hash(newPassword, saltRounds);

    await updateUserPassword(userId, hashedPassword);

    const user = await findUserById(userId);

    await sendPasswordChangeConfirmationEmail(user.email);

    res.status(200).json({ message: 'Mot de passe réinitialisé avec succès' });
  } catch (err) {
    return res.status(400).json({ error: 'Token invalide ou expiré' });
  }
}

module.exports = { forgotPassword, resetPassword };
