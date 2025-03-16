import axios from 'axios';

const axiosInstance = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:5298' : ''
});

export default {
    install(app) {
      app.config.globalProperties.$axios = axiosInstance;
    }
  };