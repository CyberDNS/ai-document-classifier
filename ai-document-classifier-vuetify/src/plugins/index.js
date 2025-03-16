/**
 * plugins/index.js
 *
 * Automatically included in `./src/main.js`
 */

// Plugins
import vuetify from './vuetify'
import axios from './axiosPlugin'
import pinia from '@/stores'
import router from '@/router'

export function registerPlugins (app) {
  app
    .use(vuetify)
    .use(axios)
    .use(router)
    .use(pinia)
}
