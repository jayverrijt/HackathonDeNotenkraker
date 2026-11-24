import { ApiObstacleRepository } from './ApiObstacleRepository';
import { SqliteObstacleRepository } from './SqliteObstacleRepository';

const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE ?? 'sqlite';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api';

export const obstacleRepository =
    DATA_SOURCE === 'api'
        ? new ApiObstacleRepository(API_BASE_URL)
        : new SqliteObstacleRepository();