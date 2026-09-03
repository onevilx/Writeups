const fs              = require('fs');
const bot             = require('../bot');
const path            = require('path');
const express         = require('express');
const router          = express.Router();
const NodeCache       = require('node-cache');
const JWTHelper       = require('../helpers/JWTHelper');
const AuthMiddleware  = require('../middleware/AuthMiddleware');

const cache = new NodeCache({ stdTTL: 60 })
const response = data => ({ message: data });
let db;

router.get('/', AuthMiddleware, (req, res) => {
	return res.render('index.html')
});

router.get('/api/settings', AuthMiddleware, (req, res, next) => {
	cacheKey = `_${req.headers.host}_${req.url}_${(req.headers['x-forwarded-for'] || req.ip)}`;
	if (cache.has(cacheKey)) return res.send(JSON.parse(cache.get(cacheKey)));
	return db.getUser(req.data.username)
		.then(user => {
			userSettings = JSON.parse(user.settings);
			cache.set(cacheKey, user.settings);
			res.send(userSettings);
		})
		.catch(() => res.send(response('Something went wrong!')));
});

router.post('/api/settings', AuthMiddleware, (req, res) => {
	cacheKey = `_${req.headers.host}_${req.url}_${(req.headers['x-forwarded-for'] || req.ip)}`;
	if (cache.has(cacheKey)) cache.del(cacheKey);
	return db.getUser(req.data.username)
		.then(user => {
			if (req.is('*/json')) {
				return db.saveSettings(user.username, JSON.stringify(req.body))
					.then(() => res.send(response("Settings saved successfully!")));
			}
			return res.status(401).send(response('Invalid data supplied!'));
		});
});

router.get('/api/stub/build', AuthMiddleware, (req, res) => {
	return db.getUser(req.data.username)
		.then(user => {
			if (user.license !== "active") {
				if (req.ip !== '127.0.0.1') {
					return bot.visitPage()
						.then(() => res.send(response('User license has Expired!')));
				}
			}
			res.send(response("Stub build is in progress!"));
		});
});

router.get('/logout', (req, res) => {
	res.clearCookie('session');
	return res.redirect('/');
});

module.exports = database => {
	db = database;
	return router;
};