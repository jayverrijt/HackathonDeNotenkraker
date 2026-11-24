package nl.hackathondenotenkraker.backend.dto;

import java.time.Instant;

public record ObstacleRequest(
        String obstacleType,
        String userId,
        Instant timestamp,
        double longitude,
        double latitude
) {
}
