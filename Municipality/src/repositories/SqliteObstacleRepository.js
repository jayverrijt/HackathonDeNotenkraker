import { getSqliteDb } from '../database/sqliteClient';
import { ObstacleRepository } from './ObstacleRepository';

function mapRowToObstacle(row) {
    return {
        id: Number(row.id),
        name: String(row.name),
        address: String(row.address),
        reporterUid: String(row.reporter_uid),
        reportDate: String(row.report_date),
        lat: Number(row.lat),
        lng: Number(row.lng),
    };
}

export class SqliteObstacleRepository extends ObstacleRepository {
    async getAll() {
        const db = await getSqliteDb();
        const stmt = db.prepare('SELECT * FROM obstacles ORDER BY id ASC');
        const results = [];

        while (stmt.step()) {
            results.push(mapRowToObstacle(stmt.getAsObject()));
        }
        stmt.free();

        return results;
    }

    async getById(id) {
        const db = await getSqliteDb();
        const stmt = db.prepare('SELECT * FROM obstacles WHERE id = ?');
        stmt.bind([id]);

        const obstacle = stmt.step() ? mapRowToObstacle(stmt.getAsObject()) : null;
        stmt.free();

        return obstacle;
    }

    async update(id, payload) {
        const db = await getSqliteDb();
        db.run('UPDATE obstacles SET name = ? WHERE id = ?', [payload.name.trim(), id]);

        const updated = await this.getById(id);
        if (!updated) throw new Error(`Obstakel met id ${id} niet gevonden.`);
        return updated;
    }

    async delete(id) {
        const db = await getSqliteDb();
        db.run('DELETE FROM obstacles WHERE id = ?', [id]);
    }
}