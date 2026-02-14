const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { createUser, findUser, searchUsers } = require('../model/userModel');
const { sendConfirmationEmail } = require('../config/mailer');

// fonction qui permet d'enregistrer un nouvel utilisateur
async function register(req, res) {
  const { email, nom, prenom, password, role } = req.body;
  
  // Vérifier que les champs requis sont fournis
  if (!email || !nom || !prenom || !password || !role) { // requiert egalement le role pour l'inscription de l'utilisateur
    return res.status(400).json({ error: "Email, nom, prenom, password et role sont requis." });
  }
  
  try {
    // Vérifier si un utilisateur existe déjà (par email)
    const existingUser = await findUser(email);
    if (existingUser) {
      return res.status(400).json({ error: "Un utilisateur avec cet email existe déjà." });
    }
    
    // Hacher le mot de passe
    const saltRounds = 10;
    const hashedPassword = await bcrypt.hash(password, saltRounds);
    
    // Créer l'utilisateur dans la base de données
    const newUser = await createUser(email, nom, prenom, hashedPassword, role);

    // Envoyer l'e-mail de confirmation ici
    await sendConfirmationEmail(email, prenom);
    
    // On ne retourne pas le mot de passe
    delete newUser.password;
    return res.status(201).json({ message: "Utilisateur créé avec succès.", user: newUser });
  } catch (err) {
    console.error("Erreur lors de l'inscription :", err);
    return res.status(500).json({ error: "Erreur interne du serveur." });
  }
}

// fonction qui permet de vérifier la connexion d'un utilisateur
async function login(req, res) {
  const { email, password } = req.body;
  
  // Vérifier que les champs sont fournis
  if (!email || !password) {
    return res.status(400).json({ error: "L'email et le mot de passe sont requis." });
  }
  
  try {
    // Recherche l'utilisateur par son email
    const user = await findUser(email);
    
    // Si l'utilisateur n'existe pas
    if (!user) {
      return res.status(401).json({ error: "Identifiants invalides." });
    }
    
    // Vérification du mot de passe
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(401).json({ error: "Identifiants invalides." });
    }
    
    // Générer un token JWT
    const token = jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      process.env.JWT_SECRET,
      { expiresIn: '1h' }
    );
    
    // Supprimer le mot de passe de l'objet user avant de l'envoyer dans la réponse
    delete user.password;
    
    return res.status(200).json({ message: "Connexion réussie.", user, token });
  } catch (err) {
    console.error("Erreur lors de la connexion :", err);
    return res.status(500).json({ error: "Erreur interne du serveur." });
  }
}

// Fonction de recherche d'utilisateurs
async function searchUsersController(req, res) {
  try {
    const query = req.query.q;
    if (!query) {
      return res.status(400).json({ error: "La requête de recherche est manquante." });
    }
    const users = await searchUsers(query);
    res.json({ users });
  } catch (err) {
    console.error("Erreur lors de la recherche des utilisateurs :", err);
    res.status(500).json({ error: "Erreur interne du serveur." });
  }
}

module.exports = { register, login, searchUsersController };
