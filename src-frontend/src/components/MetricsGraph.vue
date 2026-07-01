<template>
  <apexchart
    style="width: 100%"
    type="line"
    :options="options"
    :series="series"
  ></apexchart>
</template>

<script>
import formatMixin from 'src/mixins/formatMixin';

export default {
  name: 'MetricsGraph',
  mixins: [formatMixin],
  props: {
    metricsData: {
      type: Array,
      default: () => [],
    },
    id: {
      type: String,
      default: '',
    },
  },
  data() {
    return {};
  },
  mounted() {
    setTimeout(() => {
      const chart = ApexCharts.getChartByID('metrics-graph-' + this.id);
      chart.hideSeries('Inactive Member');
      chart.hideSeries('Account Only');
      chart.hideSeries('New Member');
    }, 0); // triggers on the next dom update
  },
  computed: {
    options() {
      return {
        chart: {
          id: 'metrics-graph-' + this.id,
        },
        xaxis: {
          categories: this.metricsData.map((item) =>
            this.formatDate(item.date)
          ),
        },
        theme: {
          mode: this.$q.dark.isActive ? 'dark' : 'light',
        },
        yaxis: {
          labels: {
            formatter: function (val) {
              return val.toFixed(0);
            },
            min: 0,
          },
        },
      };
    },
    series() {
      // First pass: collect all known state keys across all snapshots
      let allKeys = new Set();
      this.metricsData.forEach((item) => {
        if (Array.isArray(item.data)) {
          item.data.forEach((state) => {
            const key = state?.state ?? state?.type;
            if (key) allKeys.add(key);
          });
        } else {
          allKeys.add('value');
        }
      });

      // Second pass: build aligned arrays — null for any state missing from a snapshot
      let states = {};
      allKeys.forEach((key) => (states[key] = []));
      this.metricsData.forEach((item) => {
        if (Array.isArray(item.data)) {
          allKeys.forEach((key) => {
            const entry = item.data.find((s) => (s?.state ?? s?.type) === key);
            states[key].push(entry ? entry.total : null);
          });
        } else {
          allKeys.forEach((key) => {
            states[key].push(key === 'value' ? item.data.value : null);
          });
        }
      });

      return Object.keys(states).map((state) => {
        return {
          name: this.$t('stats.labels.' + state),
          data: states[state],
        };
      });
    },
  },
};
</script>
