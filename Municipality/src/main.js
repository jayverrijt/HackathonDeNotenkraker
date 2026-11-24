import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import './style.css'; // Zorg dat Tailwind hierin staat

createApp(App).use(router).mount('#app');