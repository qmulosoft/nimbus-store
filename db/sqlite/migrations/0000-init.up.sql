CREATE TABLE local_file
(
    id CHAR(32) PRIMARY KEY,
    path VARCHAR NOT NULL
);

CREATE TABLE bucket
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    desc VARCHAR
);

CREATE TABLE file
(
    id CHAR(36) PRIMARY KEY,
    name VARCHAR NOT NULL,
    mime VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    pending BOOLEAN DEFAULT TRUE NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    local_file_id CHAR(32),
    bucket_id INT NOT NULL,
    FOREIGN KEY(local_file_id) REFERENCES local_file(id),
    FOREIGN KEY(bucket_id) REFERENCES bucket(id)
);

CREATE TRIGGER [UpdateFileLastUpdate]
    AFTER UPDATE
    ON file
    FOR EACH ROW
    BEGIN
        UPDATE file SET last_updated = CURRENT_TIMESTAMP WHERE id = OLD.id;
    end;