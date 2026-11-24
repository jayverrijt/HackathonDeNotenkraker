package nl.hackathondenotenkraker.backend.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "obstacles")
public class Obstacle {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String obstacleType;

    private String userId;

    private Instant timestamp;

    private double longitude;

    private double latitude;

    public Obstacle() {
    }

    // Getters
    public Long getId() {
        return id;
    }

    public String getObstacleType() {
        return obstacleType;
    }

    public String getUserId() {
        return userId;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public double getLongitude() {
        return longitude;
    }

    public double getLatitude() {
        return latitude;
    }

    // Setters
    public void setId(Long id) {
        this.id = id;
    }

    public void setObstacleType(String obstacleType) {
        this.obstacleType = obstacleType;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public void setLongitude(double longitude) {
        this.longitude = longitude;
    }

    public void setLatitude(double latitude) {
        this.latitude = latitude;
    }
}