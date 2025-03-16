<template>
  <v-container>
    <v-row>
      <v-col>
        <v-btn @click="prevDocument" :disabled="currentIndex === 0" v-if="documents.length > 0">Previous</v-btn>
        <v-btn @click="nextDocument" :disabled="currentIndex === documents.length - 1" v-if="documents.length > 0">Next</v-btn>
        <v-btn @click="fetchDocuments">Refresh</v-btn>
        <span v-if="documents.length > 0">{{ currentIndex + 1 }}/{{ totalDocuments }}</span>
      </v-col>
    </v-row>
    <v-row v-if="documents.length > 0">
      <v-col cols="12" md="8">
        <v-card v-if="currentDocument" class="document-card">
          <v-card-title>{{ currentDocument }}</v-card-title>
          <v-card-text class="document-card-text">
            <embed :src="documentUrl" type="application/pdf" class="document-embed" />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4" class="d-flex flex-column">
        <v-text-field v-model="metadata.date" label="Date" class="flex-grow-0" />
        <v-combobox v-model="metadata.category" :items="categories" label="Category" class="flex-grow-0">
          <template v-slot:append-item>
            <v-list-item v-if="!categories.includes(metadata.category)">
              <v-btn @click="addCategory">Add</v-btn>
            </v-list-item>
          </template>
        </v-combobox>
        <v-combobox v-model="metadata.source" :items="sources" label="Source" class="flex-grow-0">
          <template v-slot:append-item>
            <v-list-item v-if="!sources.includes(metadata.source)">
              <v-btn @click="addSource">Add</v-btn>
            </v-list-item>
          </template>
        </v-combobox>
        <v-combobox v-model="metadata.destination" :items="destinations" label="Destination" class="flex-grow-0">
          <template v-slot:append-item>
            <v-list-item v-if="!destinations.includes(metadata.destination)">
              <v-btn @click="addDestination">Add</v-btn>
            </v-list-item>
          </template>
        </v-combobox>
        <v-text-field v-model="metadata.name" label="Name" class="flex-grow-0" />
        <v-textarea v-model="metadata.description" label="Description" class="flex-grow-1" />
      </v-col>
    </v-row>
    <v-form @submit.prevent="saveFile" v-if="documents.length > 0">
      <v-row>
        <v-col cols="12">
          <v-container>
            <v-row align="center">
              <v-col>
                <v-text-field v-model="proposedFileName" label="Filename" />
              </v-col>
              <v-col cols="2">
                <v-btn type="submit">
                  Save File
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
export default {
  data() {
    return {
      documents: [],
      currentIndex: 0,
      totalDocuments: 0,
      metadata: {
        date: '',
        category: '',
        source: '',
        destination: '',
        name: '',
        description: ''
      },
      categories: [],
      sources: [],
      destinations: []
    };
  },
  computed: {
    currentDocument() {
      return this.documents[this.currentIndex];
    },
    documentUrl() {
      const baseURL = this.$axios.defaults.baseURL;
      return `${baseURL}/documents/${this.currentDocument}`;
    },
    proposedFileName() {
      const formattedDate = this.metadata.date.replace(/-/g, '');
      return `${formattedDate}-${this.metadata.source}-${this.metadata.destination}-${this.metadata.name}.pdf`;
    }
  },
  mounted() {
    this.fetchDocuments();
    this.fetchConfig();
    this.setupSSE();
  },
  methods: {
    async fetchDocuments() {
      try {
        const response = await this.$axios.get('/documents');
        this.documents = response.data;
        this.totalDocuments = this.documents.length;
        this.fetchMetadata();
      } catch (error) {
        console.error('Error fetching documents:', error);
      }
    },
    async fetchMetadata() {
      if (this.currentDocument) {
        try {
          const response = await this.$axios.get(`/documents/${this.currentDocument}/metadata`);
          this.metadata = response.data;
        } catch (error) {
          console.error('Error fetching metadata:', error);
        }
      }
    },
    async fetchConfig() {
      try {
        const [categoriesResponse, sourcesResponse, destinationsResponse] = await Promise.all([
          this.$axios.get('/config/categories'),
          this.$axios.get('/config/sources'),
          this.$axios.get('/config/destinations')
        ]);
        this.categories = categoriesResponse.data;
        this.sources = sourcesResponse.data;
        this.destinations = destinationsResponse.data;
      } catch (error) {
        console.error('Error fetching config:', error);
      }
    },
    async saveFile() {
      try {
        await this.$axios.post('/documents/save', {
          originalFilename: this.currentDocument,
          renamedFilename: this.proposedFileName,
          metadata: this.metadata
        });
        this.fetchDocuments();
      } catch (error) {
        console.error('Error saving file and metadata:', error);
      }
    },
    async addCategory() {
      try {
        await this.$axios.post('/config/categories', { category: this.metadata.category });
        this.fetchConfig();
      } catch (error) {
        console.error('Error adding category:', error);
      }
    },
    async addSource() {
      try {
        await this.$axios.post('/config/sources', { source: this.metadata.source });
        this.fetchConfig();
      } catch (error) {
        console.error('Error adding source:', error);
      }
    },
    async addDestination() {
      try {
        await this.$axios.post('/config/destinations', { destination: this.metadata.destination });
        this.fetchConfig();
      } catch (error) {
        console.error('Error adding destination:', error);
      }
    },
    nextDocument() {
      if (this.currentIndex < this.documents.length - 1) {
        this.currentIndex++;
        this.fetchMetadata();
      }
    },
    prevDocument() {
      if (this.currentIndex > 0) {
        this.currentIndex--;
        this.fetchMetadata();
      }
    },
    setupSSE() {
      const baseURL = this.$axios.defaults.baseURL;
      const eventSource = new EventSource(`${baseURL}/sse/documents`);
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.totalDocuments = data.totalDocuments;
        this.fetchDocuments();
      };
    }
  }
};
</script>

<style scoped>
.document-embed {
  width: 100%;
  height: 1100px;
}
</style>
