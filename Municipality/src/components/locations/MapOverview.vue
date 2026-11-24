<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Minus, Plus, Search } from 'lucide-vue-next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const props = defineProps({
  obstacles: { type: Array, required: true },
  selectedId: { type: Number, default: null },
  areaQuery: { type: String, default: '' },
});

const emit = defineEmits(['select', 'update:areaQuery']);

const mapContainer = ref(null);
let map = null;
let markersLayer = null;

function createPinIcon(number, isSelected) {
  const classes = isSelected
      ? 'bg-[#1C1D1B] text-white border-[#1C1D1B] scale-110 shadow-sm'
      : 'bg-white text-[#1C1D1B] border-[#C6C6BE] hover:border-[#1C1D1B]';

  return L.divIcon({
    className: 'custom-osm-pin',
    html: `<div class="flex h-9 w-9 items-center justify-center rounded-full border text-xs font-semibold tabular-nums transition-all duration-150 ${classes}">${number}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

function renderMarkers() {
  if (!map || !markersLayer) return;

  markersLayer.clearLayers();

  props.obstacles.forEach((obstacle, index) => {
    const isSelected = obstacle.id === props.selectedId;

    const marker = L.marker([obstacle.lat, obstacle.lng], {
      icon: createPinIcon(index + 1, isSelected),
      zIndexOffset: isSelected ? 1000 : 0,
    });

    marker.on('click', () => {
      emit('select', obstacle.id);
    });

    marker.addTo(markersLayer);
  });
}

onMounted(() => {
  const defaultCenter = props.obstacles[0]
      ? [props.obstacles[0].lat, props.obstacles[0].lng]
      : [51.4416, 5.4697];

  map = L.map(mapContainer.value, {
    center: defaultCenter,
    zoom: 13,
    zoomControl: false, // We gebruiken onze eigen + / - knoppen
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
  renderMarkers();

  // Zorg dat alle pins direct netjes in beeld passen
  if (props.obstacles.length > 1) {
    const bounds = L.latLngBounds(props.obstacles.map((o) => [o.lat, o.lng]));
    map.fitBounds(bounds, { padding: [50, 50] });
  }
});

watch(
    () => [props.obstacles, props.selectedId],
    () => {
      renderMarkers();

      // Pan soepel naar de geselecteerde locatie
      const selected = props.obstacles.find((o) => o.id === props.selectedId);
      if (selected && map) {
        map.panTo([selected.lat, selected.lng], { animate: true });
      }
    },
    { deep: true }
);

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
  }
});

function handleZoomIn() {
  map?.zoomIn();
}

function handleZoomOut() {
  map?.zoomOut();
}
</script>

<template>
  <section
      aria-labelledby="map-overview-heading"
      class="flex flex-col overflow-hidden rounded-xl border border-[#E5E5E0] bg-white"
  >
    <div class="flex items-center justify-between border-b border-[#E5E5E0] px-5 py-4">
      <h2 id="map-overview-heading" class="text-sm font-semibold text-[#1C1D1B]">
        Map overview
      </h2>
      <span class="text-xs font-medium tabular-nums text-[#646660]">
        {{ obstacles.length }} {{ obstacles.length === 1 ? 'location' : 'locations' }}
      </span>
    </div>

    <div class="relative h-80 w-full overflow-hidden bg-[#ECECE8] sm:h-[460px] lg:h-[580px]">
      <!-- Zoekveld boven de kaart (z-[400] om boven Leaflet-panes te blijven) -->
      <div class="absolute left-4 top-4 z-[400] w-56 max-w-[calc(100%-2rem)]">
        <label for="map-area-search" class="sr-only">Search this area</label>
        <div class="relative">
          <Search
              aria-hidden="true"
              class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767872]"
          />
          <input
              id="map-area-search"
              type="search"
              :value="areaQuery"
              placeholder="Search this area"
              class="h-10 w-full rounded-lg border border-[#DCDCD6] bg-white pl-9 pr-3 text-sm text-[#1C1D1B] placeholder:text-[#8A8C85] shadow-xs focus:border-[#1C1D1B] focus:outline-none"
              @input="emit('update:areaQuery', $event.target.value)"
          />
        </div>
      </div>

      <!-- Leaflet OSM-container -->
      <div ref="mapContainer" class="h-full w-full z-0" />

      <!-- Eigen zoom-knoppen -->
      <div class="absolute bottom-8 right-4 z-[400] flex flex-col overflow-hidden rounded-lg border border-[#DCDCD6] bg-white shadow-xs">
        <button
            type="button"
            aria-label="Zoom in"
            class="flex h-11 w-11 items-center justify-center border-b border-[#E5E5E0] text-[#1C1D1B] transition-colors hover:bg-[#F3F3F0] focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#1C1D1B]"
            @click="handleZoomIn"
        >
          <Plus class="h-4 w-4" />
        </button>
        <button
            type="button"
            aria-label="Zoom out"
            class="flex h-11 w-11 items-center justify-center text-[#1C1D1B] transition-colors hover:bg-[#F3F3F0] focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#1C1D1B]"
            @click="handleZoomOut"
        >
          <Minus class="h-4 w-4" />
        </button>
      </div>
    </div>
  </section>
</template>