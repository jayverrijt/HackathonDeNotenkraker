import { createRouter, createWebHistory } from 'vue-router';
import AppShell from '../layouts/AppShell.vue';
import LocationsDashboardPage from '../pages/LocationsDashboardPage.vue';
import EditObstaclePage from '../pages/EditObstaclePage.vue';

const routes = [
    {
        path: '/',
        component: AppShell,
        children: [
            {
                path: '',
                name: 'locations-dashboard',
                component: LocationsDashboardPage,
            },
            {
                path: 'locations/:id/edit',
                name: 'obstacle-edit',
                component: EditObstaclePage,
            },
        ],
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/',
    },
];

export const router = createRouter({
    history: createWebHistory(),
    routes,
});