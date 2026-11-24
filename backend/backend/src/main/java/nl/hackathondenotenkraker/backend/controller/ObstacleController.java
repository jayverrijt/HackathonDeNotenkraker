package nl.hackathondenotenkraker.backend.controller;

import nl.hackathondenotenkraker.backend.model.Obstacle;
import nl.hackathondenotenkraker.backend.repository.ObstacleRepository;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/obstacles")
public class ObstacleController {

    private final ObstacleRepository obstacleRepository;

    public ObstacleController(ObstacleRepository obstacleRepository) {
        this.obstacleRepository = obstacleRepository;
    }

    @PostMapping
    public Obstacle createObstacle(@RequestBody Obstacle obstacle) {
        return obstacleRepository.save(obstacle);
    }
}
