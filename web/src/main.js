import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import ToastService from 'primevue/toastservice';
// import Toast from 'primevue/toast';
import Toast from 'vue-toastification';
import PrimeVue from 'primevue/config';
import Button from 'primevue/button';
import './index.css'

import {createRouter, createWebHistory} from "vue-router";
import Home from './views/Home.vue'
import BatchRecord from './views/BatchRecord.vue'

// Define route components
const routes = [
    {
        path: '/',
        name: 'home',
        component: Home
    },
    {
        path: '/batch-record/:count(\\d+)',
        name: 'batch-record',
        component: BatchRecord
    }
];

export const router = createRouter ({
    history: createWebHistory(),
    routes
});
const app = createApp(App);
app.use(PrimeVue);  // Use PrimeVue
app.use(ToastService);

// Register Button and Toast components globally
app.component('Button', Button);
app.component('Toast', Toast);
app.use(router).mount('#app');