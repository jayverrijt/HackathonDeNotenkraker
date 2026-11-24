package nl.hackathondenotenkraker.backend.repository;


import nl.hackathondenotenkraker.backend.model.Obstacle;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ObstacleRepository extends JpaRepository<Obstacle, Long> {
}
