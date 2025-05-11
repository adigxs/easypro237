import {createRouter, createWebHistory} from "vue-router";
import BatchRecord from './views/BatchRecord.vue'

// Define route components
const routes = [
  { path: '/batch-record:count(\\d+)?', component: BatchRecord },
];

export const router = createRouter ({
    history: createWebHistory(),
    routes

})