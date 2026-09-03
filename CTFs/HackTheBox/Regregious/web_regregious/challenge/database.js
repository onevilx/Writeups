const sqlite = require('sqlite-async');

class Database {
	constructor(db_file) {
		this.db_file = db_file;
		this.db = undefined;
	}
	
	async connect() {
		this.db = await sqlite.open(this.db_file);
	}

	async migrate() {
		return this.db.exec(`
            DROP TABLE IF EXISTS userData;

            CREATE TABLE IF NOT EXISTS userData (
                id         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                username   VARCHAR(255) NOT NULL UNIQUE,
                license    VARCHAR(255) NOT NULL,
                settings    TEXT NOT NULL
            );
        `);
	}

	async registerUser(username) {
		return new Promise(async (resolve, reject) => {
			try {
				let stmt = await this.db.prepare("INSERT INTO userData (username, license, settings) VALUES ( ?, 'null', '{\"protect_process\":\"true\",\"random_assembly\":\"true\",\"amsi_bypass\":\"true\",\"delay\":\"false\",\"anti_vm\":\"true\",\"kill_defender\":\"false\",\"lan_spreading\":\"true\",\"inclusion_list\":\"jpg, jpeg, png, ods, xls, xlsx, csv, ics, vcf, 3dm, 3ds, max, bmp, dds, gif, psd, xcf, tga, thm, tif, tiff, yuv, ai, eps, ps, svg, dwg, dxf, gpx, kml, kmz, webp, 3g2, 3gp, aaf, asf, avchd, avi, drc, flv, m2v, m4p, m4v, mkv, mng, mov, mp2, mp4, mpe, mpeg, mpg, mpv, mxf, nsv, ogg, ogv, ogm, qt, rm, rmvb, roq, srt, svi, vob, webm, wmv, yuv, aac, aiff, ape, au, flac, gsm, it, m3u, m4a, mid, mod, mp3, mpa, pls, ra, s3m, sid, wav, wma, xm, 7z, a, apk, ar, bz2, cab, cpio, deb, dmg, egg, gz, iso, jar, lha, mar, pea, rar, rpm, s7z, shar, tar, tbz2, tgz, tlz, war, whl, xpi, zip, zipx, xz, pak, exe, msi, bat, crx, patch, html, js, html, htm, css, js, jsx, scss, php, java, ppt, odp, doc, docx, ebook, log, md, msg, odt, org, pages, pdf, rtf, rst, tex, txt\",\"exclusion_list\":\"\",\"encrypted_ext\":\".htb\",\"btc_address\":\"BTC ADDRESS\",\"ransom_message\":\"Attention! all your important files were encrypted! To get your files back send 1337 USD worth in Bitcoins to the address below, visit the TOR website and submit your Unique Identifier Key.\\n\\nYou can purchase Bitcoins from the following websites:\\n\\nhttps:\/\/localbitcoins.com\\nhttps:\/\/coinbase.com\\n\\nBTC Address : [[ BTC_ADDRESS ]]\\n\\nTOR Website : raascxoysz2kvblluinr4ubak5pluunduy7qqd.onion\",\"ico_url\":\"\/static\/images\/burns.ico\"}')");
				resolve((await stmt.run(username)));
			} catch(e) {
				reject(e);
			}
		});
	}

	async getUser(user) {
		return new Promise(async (resolve, reject) => {
			try {
				let stmt = await this.db.prepare("SELECT * FROM userData WHERE username = ?");
				resolve(await stmt.get(user));
			} catch(e) {
				console.log(e);
				reject(e);
			}
		});
	}

	async saveSettings(username, settings) {
		return new Promise(async (resolve, reject) => {
			try {
				let stmt = await this.db.prepare('UPDATE userData SET settings = ? WHERE username = ?');
				resolve(await stmt.get(settings, username));
			} catch(e) {
				reject(e);
			}
		});
	}

}

module.exports = Database;