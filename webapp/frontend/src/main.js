
import { createApp } from 'vue'
import App from './App.vue'
import {createBootstrap} from 'bootstrap-vue-next'
import vSelect from 'vue-select'

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css'
import 'vue-select/dist/vue-select.css'
import 'bootstrap-icons/font/bootstrap-icons.min.css'

const app = createApp(App)
app.use(createBootstrap())
app.component('v-select', vSelect)
app.mount('#app')
