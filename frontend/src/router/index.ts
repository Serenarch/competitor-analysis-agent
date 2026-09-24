
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('@/views/Analysis.vue'),
  },
  {
    path: '/report/:id',
    name: 'report',
    component: () => import('@/views/Report.vue'),
  },
  {
  path: '/history',
  name: 'history',
    component: () => import('@/views/History.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router