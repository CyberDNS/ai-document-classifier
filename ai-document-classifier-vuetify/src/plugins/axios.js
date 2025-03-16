import axios from 'axios';

let instance;

// Fetch the configuration file
fetch('/config.json')
  .then(response => response.json())
  .then(config => {
    const baseUrl = config.VUE_APP_API_URL || 'http://localhost:5298';

    // Create the axios instance with the fetched base URL
    instance = axios.create({
      baseURL: baseUrl,
    });

    export default instance;
  })
  .catch(error => {
    console.error('Error fetching configuration:', error);
    // Create the axios instance with the default base URL
    instance = axios.create({
      baseURL: 'http://localhost:5298',
    });

    export default instance;
  });