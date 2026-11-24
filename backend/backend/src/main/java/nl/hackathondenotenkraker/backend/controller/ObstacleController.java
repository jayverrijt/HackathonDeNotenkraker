package nl.hackathondenotenkraker.backend.controller;

import nl.hackathondenotenkraker.backend.dto.ObstacleRequest;
import nl.hackathondenotenkraker.backend.dto.ObstacleResponse;
import nl.hackathondenotenkraker.backend.dto.ObstacleUpdateRequest;
import nl.hackathondenotenkraker.backend.model.Obstacle;
import nl.hackathondenotenkraker.backend.repository.ObstacleRepository;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

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

    @GetMapping("/{id}")
    public ObstacleResponse getObstacle(@PathVariable Long id) {
        return toResponse(findObstacle(id));
    }

    @PutMapping("/{id}")
    public ObstacleResponse updateObstacle(@PathVariable Long id, @RequestBody ObstacleUpdateRequest request) {
        if (request.obstacleType() == null || request.obstacleType().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Obstakelnaam is verplicht");
        }
        Obstacle obstacle = findObstacle(id);
        obstacle.setObstacleType(request.obstacleType().trim());
        return toResponse(obstacleRepository.save(obstacle));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteObstacle(@PathVariable Long id) {
        obstacleRepository.delete(findObstacle(id));
    }

    private Obstacle findObstacle(Long id) {
        return obstacleRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Obstakel niet gevonden"));
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
