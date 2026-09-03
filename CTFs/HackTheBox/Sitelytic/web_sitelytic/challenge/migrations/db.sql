DROP TABLE IF EXISTS subscriber;
CREATE TABLE subscriber (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    email VARCHAR(255) DEFAULT NULL,
    token VARCHAR(255) DEFAULT NULL
);

DROP TABLE IF EXISTS service;
CREATE TABLE service (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    service VARCHAR(255) DEFAULT NULL,
    host VARCHAR(255) DEFAULT NULL,
    headers VARCHAR(500) DEFAULT NULL,
    status INTEGER DEFAULT 1
);
INSERT INTO service (service, host, headers, status)
VALUES
    ("Backend", "http://192.168.0.103:8080/status", "X-Auth: a7b70667e126a9110e2d8b40c28e8602", 1),
    ("Frontend", "https://sitelytics.htb/status", "", 1),
    ("API", "http://192.168.0.102/api/status", "X-Api-Key: a7b70667e126a9110e2d8b40c28e8602", 2),
    ("Payments", "http://192.168.0.105:6000/payments/status", "X-Auth: a7b70667e126a9110e2d8b40c28e8602", 1),
    ("Helpdesk", "https://helpdesk.sitelytics.htb/payments/status", "X-Auth: a7b70667e126a9110e2d8b40c28e8602", 3);

DROP TABLE IF EXISTS user;
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username VARCHAR(255) DEFAULT NULL,
    password VARCHAR(255) DEFAULT NULL
);
INSERT INTO user (username, password) VALUES ("admin", "admin");