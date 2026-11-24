package nl.hackathondenotenkraker.backend.controller;

import nl.hackathondenotenkraker.backend.dto.ObstacleUpdateRequest;
import nl.hackathondenotenkraker.backend.model.Obstacle;
import nl.hackathondenotenkraker.backend.repository.ObstacleRepository;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ObstacleControllerTests {
    private final ObstacleRepository repository = mock(ObstacleRepository.class);
    private final ObstacleController controller = new ObstacleController(repository);

    @Test
    void updatingNamePreservesReportAndLocation() {
        Obstacle obstacle = new Obstacle();
        obstacle.setId(1L);
        obstacle.setObstacleType("Tegel");
        obstacle.setUserId("reporter-123");
        obstacle.setTimestamp(Instant.parse("2026-11-24T13:00:00Z"));
        obstacle.setLatitude(51.4416);
        obstacle.setLongitude(5.4697);
        when(repository.findById(1L)).thenReturn(Optional.of(obstacle));
        when(repository.save(obstacle)).thenReturn(obstacle);

        var response = controller.updateObstacle(1L, new ObstacleUpdateRequest(" Losse tegel "));

        assertEquals("Losse tegel", response.obstacleType());
        assertEquals("reporter-123", response.userId());
        assertEquals(obstacle.getTimestamp(), response.timestamp());
        assertEquals(51.4416, response.latitude());
        assertEquals(5.4697, response.longitude());
        verify(repository).save(obstacle);
    }

    @Test
    void missingObstacleReturnsNotFound() {
        when(repository.findById(99L)).thenReturn(Optional.empty());
        var error = assertThrows(ResponseStatusException.class, () -> controller.getObstacle(99L));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void blankNameIsRejectedWithoutSaving() {
        var error = assertThrows(ResponseStatusException.class,
                () -> controller.updateObstacle(1L, new ObstacleUpdateRequest(" ")));
        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verifyNoInteractions(repository);
    }

    @Test
    void deletingRemovesTheRequestedObstacle() {
        Obstacle obstacle = new Obstacle();
        obstacle.setId(1L);
        when(repository.findById(1L)).thenReturn(Optional.of(obstacle));
        controller.deleteObstacle(1L);
        verify(repository).delete(obstacle);
    }
}
