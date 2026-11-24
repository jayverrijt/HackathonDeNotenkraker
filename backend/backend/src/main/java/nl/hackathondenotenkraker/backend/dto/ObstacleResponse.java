package nl.hackathondenotenkraker.backend.dto;

import java.time.Instant;

public record ObstacleResponse(
        Long id,
        String obstacleType,
        String userId,
        Instant timestamp,
        double longitude,
        double latitude
) {
}
