import initSqlJs from 'sql.js';
import { CREATE_OBSTACLES_TABLE_SQL, SEED_OBSTACLES } from './seed';

let dbInstance = null;

export async function getSqliteDb() {
    if (dbInstance) return dbInstance;

    const init = typeof initSqlJs === 'function' ? initSqlJs : initSqlJs.default;

    const SQL = await init({
        locateFile: () => '/sql-wasm.wasm',
    });

    const db = new SQL.Database();
    db.run(CREATE_OBSTACLES_TABLE_SQL);

    const stmt = db.prepare(`
        INSERT INTO obstacles (name, address, reporter_uid, report_date, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?)
    `);

    for (const item of SEED_OBSTACLES) {
        stmt.run([
            item.name,
            item.address,
            item.reporterUid,
            item.reportDate,
            item.lat,
            item.lng,
        ]);
    }
    stmt.free();

    dbInstance = db;
    return dbInstance;
}