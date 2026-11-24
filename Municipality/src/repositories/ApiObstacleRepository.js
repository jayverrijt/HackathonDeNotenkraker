import { ObstacleRepository } from './ObstacleRepository';

function mapObstacle(obstacle) {
    return {
        id: obstacle.id,
        name: obstacle.obstacleType ?? '',
        address: `${obstacle.latitude}, ${obstacle.longitude}`,
        reporterUid: obstacle.userId ?? '',
        reportDate: obstacle.timestamp
            ? new Date(obstacle.timestamp).toLocaleDateString('nl-NL')
            : '',
        lat: obstacle.latitude,
        lng: obstacle.longitude,
    };
}

export class ApiObstacleRepository extends ObstacleRepository {
    constructor(baseUrl) {
        super();
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    async getAll() {
        const res = await fetch(`${this.baseUrl}/obstacles`);
        if (!res.ok) throw new Error('Kan obstakels niet ophalen van de API.');
        return (await res.json()).map(mapObstacle);
    }

    async getById(id) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`);
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet ophalen.`);
        return mapObstacle(await res.json());
    }

    async update(id, payload) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ obstacleType: payload.name }),
        });
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet bijwerken.`);
        return mapObstacle(await res.json());
    }

    async delete(id) {
        const res = await fetch(`${this.baseUrl}/obstacles/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`Kan obstakel ${id} niet verwijderen.`);
    }
}
