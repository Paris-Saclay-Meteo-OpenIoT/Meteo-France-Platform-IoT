const express = require('express');
const { check, validationResult } = require('express-validator');
const { register, login, searchUsersController } = require('../controller/userController');
const loginLimiter = require('../middleware/loginLimiter');

const router = express.Router();

// Route d'inscription de l'utilisateur avec validation
router.post('/register', [
    check('email')
      .isEmail()
      .withMessage("Veuillez fournir un email valide."),
      check('nom')
      .notEmpty()
      .withMessage("Le nom est requis."),
    check('prenom')
      .notEmpty()
      .withMessage("Le prénom est requis."),
    check('password')
      .matches(/^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$/)
      .withMessage("Le mot de passe doit contenir au moins 8 caractères, dont une majuscule, une minuscule et un chiffre."),
    check('role') // source de l'erreur 400 pour de l'insription de l'utilisateur (exige l'attribution d'un role)
      .notEmpty()
      .withMessage("Le rôle est requis.")
  ], (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()){
      return res.status(400).json({ errors: errors.array() });
    }
    next();
  }, register);

// Route de connexion de l'utilisateur
router.post('/login', loginLimiter, login);

// Route de recherche d'un utilisateur
router.get('/search', searchUsersController);

module.exports = router;