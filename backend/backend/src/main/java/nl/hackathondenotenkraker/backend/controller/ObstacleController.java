package nl.hackathondenotenkraker.backend.controller;

import nl.hackathondenotenkraker.backend.dto.ObstacleRequest;
import nl.hackathondenotenkraker.backend.dto.ObstacleResponse;
import nl.hackathondenotenkraker.backend.model.Obstacle;
import nl.hackathondenotenkraker.backend.repository.ObstacleRepository;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/obstacles")
public class ObstacleController {

    private final ObstacleRepository obstacleRepository;

    public ObstacleController(ObstacleRepository obstacleRepository) {
        this.obstacleRepository = obstacleRepository;
    }

    @GetMapping
    public List<ObstacleResponse> getObstacles() {
        return obstacleRepository.findAll().stream()
                .map(this::toResponse)
                .toList();
    }

    @PostMapping
    public ObstacleResponse createObstacle(@RequestBody ObstacleRequest request) {
        Obstacle obstacle = new Obstacle();
        obstacle.setObstacleType(request.obstacleType());
        obstacle.setUserId(request.userId());
        obstacle.setTimestamp(request.timestamp());
        obstacle.setLongitude(request.longitude());
        obstacle.setLatitude(request.latitude());

        Obstacle savedObstacle = obstacleRepository.save(obstacle);
        return toResponse(savedObstacle);
    }

    private ObstacleResponse toResponse(Obstacle obstacle) {
        return new ObstacleResponse(
                obstacle.getId(),
                obstacle.getObstacleType(),
                obstacle.getUserId(),
                obstacle.getTimestamp(),
                obstacle.getLongitude(),
                obstacle.getLatitude()
        );
    }
}
