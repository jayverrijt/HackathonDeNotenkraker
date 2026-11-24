export const CREATE_OBSTACLES_TABLE_SQL = `
    CREATE TABLE IF NOT EXISTS obstacles (
                                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                                             name TEXT NOT NULL,
                                             address TEXT NOT NULL,
                                             reporter_uid TEXT NOT NULL,
                                             report_date TEXT NOT NULL,
                                             lat REAL NOT NULL,
                                             lng REAL NOT NULL
    );
`;

export const SEED_OBSTACLES = [
    {
        name: 'Foutgeparkeerde deelscooter',
        address: 'Stratumseind 42',
        reporterUid: 'reporter_001',
        reportDate: '24-11-2026',
        lat: 51.4362,
        lng: 5.4801,
    },
    {
        name: 'Gedumpte vuilniszakken op de stoep',
        address: 'Woenselse Markt 18',
        reporterUid: 'reporter_002',
        reportDate: '23-11-2026',
        lat: 51.4519,
        lng: 5.4754,
    },
    {
        name: 'Oud matras en grofvuil op trottoir',
        address: 'Stationsplein 1',
        reporterUid: 'reporter_001',
        reportDate: '24-11-2026',
        lat: 51.4433,
        lng: 5.4808,
    },
    {
        name: 'Scooter blokkeert blindengeleidestrook',
        address: 'Kleine Berg 34',
        reporterUid: 'reporter_003',
        reportDate: '22-11-2026',
        lat: 51.4375,
        lng: 5.4738,
    },
    {
        name: 'Fietswrak op het fietspad',
        address: 'Strijp-S, Torenallee 20',
        reporterUid: 'reporter_004',
        reportDate: '21-11-2026',
        lat: 51.4488,
        lng: 5.4562,
    },
    {
        name: 'Stapel kartonnen dozen op de stoep',
        address: 'Tongelresestraat 112',
        reporterUid: 'reporter_002',
        reportDate: '20-11-2026',
        lat: 51.4411,
        lng: 5.4985,
    },
    {
        name: 'Onbeheerde bouwcontainer op stoep',
        address: 'Aalsterweg 85',
        reporterUid: 'reporter_005',
        reportDate: '19-11-2026',
        lat: 51.4252,
        lng: 5.4791,
    },
    {
        name: 'Achtergelaten winkelwagen op stoep',
        address: 'Stadswandelpark 10',
        reporterUid: 'reporter_003',
        reportDate: '18-11-2026',
        lat: 51.4285,
        lng: 5.4842,
    },
];