/**
 * @typedef {Object} Obstacle
 * @property {number} id
 * @property {string} name
 * @property {string} address
 * @property {string} reporterUid
 * @property {string} reportDate
 * @property {number} mapX
 * @property {number} mapY
 */

export class ObstacleRepository {
    /** @returns {Promise<Obstacle[]>} */
    async getAll() {
        throw new Error('Method "getAll()" must be implemented.');
    }

    /**
     * @param {number} id
     * @returns {Promise<Obstacle | null>}
     */
    async getById(id) {
        throw new Error('Method "getById(id)" must be implemented.');
    }

    /**
     * @param {number} id
     * @param {{ name: string }} payload
     * @returns {Promise<Obstacle>}
     */
    async update(id, payload) {
        throw new Error('Method "update(id, payload)" must be implemented.');
    }

    /**
     * @param {number} id
     * @returns {Promise<void>}
     */
    async delete(id) {
        throw new Error('Method "delete(id)" must be implemented.');
    }
}