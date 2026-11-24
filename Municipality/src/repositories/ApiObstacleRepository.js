import { ObstacleRepository } from './ObstacleRepository';

export class ApiObstacleRepository extends ObstacleRepository {
    constructor(baseUrl) {
        super();
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    async getAll() {
        const res = await fetch(`${this.baseUrl}/obstacles`);
        if (!res.ok) throw new Error('Kan obstakels niet ophalen van de API.');
        return res.json();
    }

    async getById(id) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`);
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet ophalen.`);
        return res.json();
    }

    async update(id, payload) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet bijwerken.`);
        return res.json();
    }

    async delete(id) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet verwijderen.`);
    }
}