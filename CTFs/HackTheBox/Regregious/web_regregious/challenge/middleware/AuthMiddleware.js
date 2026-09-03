const JWTHelper = require('../helpers/JWTHelper');
const crypto    = require('crypto');

module.exports = async (req, res, next) => {
	let db = req.db;
	try{
		if (req.cookies.session === undefined) {
			let username = `agent_${crypto.randomBytes(5).toString('hex')}`;
			let token = await JWTHelper.sign({
				username
			});
			res.cookie('session', token, { maxAge: 48132000 });
			req.data = {
				username: username
			};
			return db.registerUser(username)
				.then(() => next());
		}
		return JWTHelper.verify(req.cookies.session)
			.then(username => {
				req.data = username;
				next();
			})
			.catch(() => {
				res.redirect('/logout');
			});
		
	} catch(e) {
		console.log(e);
		return res.status(500).send('Internal server error');
	}
}