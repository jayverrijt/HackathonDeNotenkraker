# Municipality-dashboard

Het dashboard gebruikt standaard de Spring Boot API en de SQLite-database van de backend.

Start de backend vanuit de projectroot in een terminal:

```powershell
cd backend/backend
.\gradlew.bat bootRun
```

Start de frontend vanuit de projectroot in een tweede terminal:

```powershell
cd Municipality
npm ci
npm run dev
```

Open de URL die Vite toont. De Vite-proxy stuurt `/api` door naar `http://localhost:8080`, ook bij `npm run preview`.

Het dashboard haalt obstakels op, toont hun coördinaten op de kaart, wijzigt hun naam (`obstacleType`) en verwijdert ze via de API. Omdat de backend geen adres opslaat, toont de lijst de coördinaten als locatie. Nieuwe obstakels kunnen via `POST /api/obstacles` worden aangemaakt en zijn na het vernieuwen van het dashboard zichtbaar.

Voor een deployment moet de webserver `/api` naar de backend doorsturen. Een andere API-basis kan via `VITE_API_BASE_URL` worden ingesteld vóór de build; een API op een andere origin vereist ook CORS-configuratie op de backend. Voor de lokale demo met browser-SQLite kan `VITE_DATA_SOURCE=sqlite` worden ingesteld; standaard staat dit op `api`.
