<template>
  <q-page class="column flex content-center" style="width: 100%">
    <q-card
      class="q-mb-none q-tabs"
      style="background-color: transparent"
      :class="{ 'q-pb-lg': $q.screen.xs }"
    >
      <q-tabs
        v-model="tab"
        align="justify"
        narrow-indicator
        class="bg-primary text-white"
      >
        <q-tab name="doors" :label="$tc('access.door', 2)" />
        <q-tab name="interlocks" :label="$tc('access.interlock', 2)" />
        <q-tab name="memberbucks" :label="$tc('access.memberbucksDevice', 2)" />
      </q-tabs>
      <q-separator />
      <q-tab-panels v-model="tab" animated>
        <q-tab-panel name="doors" class="full-width">
          <devices-list
            deviceChoice="doors"
            :tableData="doors"
            @openDevice="manageDevice"
          ></devices-list>
        </q-tab-panel>
        <q-tab-panel name="interlocks" style="width: 100%">
          <div class="row justify-end q-gutter-sm q-mb-md">
            <q-btn
              flat
              color="primary"
              :icon="icons.download"
              :label="$t('interlocks.exportCsv')"
              @click="downloadAccessCsv"
            />
            <q-btn
              color="primary"
              :icon="icons.add"
              :label="$t('interlocks.create')"
              @click="openCreateInterlock"
            />
          </div>
          <devices-list
            deviceChoice="interlocks"
            :tableData="interlocks"
            @openDevice="manageDevice"
          ></devices-list>
        </q-tab-panel>
        <q-tab-panel name="memberbucks" style="width: 100%">
          <devices-list
            deviceChoice="memberbucks-devices"
            :tableData="memberbucksDevices"
            @openDevice="manageDevice"
          ></devices-list>
        </q-tab-panel>
      </q-tab-panels>
    </q-card>

    <!-- Create interlock dialog -->
    <q-dialog v-model="createDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ $t('interlocks.create') }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input
            v-model="createForm.name"
            :label="$t('interlocks.name')"
            outlined
            dense
            maxlength="30"
          />
          <q-input
            v-model="createForm.description"
            :label="$t('interlocks.description')"
            outlined
            dense
            maxlength="500"
          />
          <q-input
            v-model="createForm.ipAddress"
            :label="$t('interlocks.ipAddress')"
            outlined
            dense
          />
        </q-card-section>
        <q-card-section v-if="createError">
          <q-banner class="bg-negative text-white">{{ createError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="$t('button.cancel')" v-close-popup />
          <q-btn
            color="primary"
            :label="$t('button.submit')"
            :loading="createLoading"
            @click="submitCreateInterlock"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import DevicesList from '@components/AdminTools/DevicesList.vue';
import DeviceDialog from '@components/AdminTools/DeviceDialog.vue';
import icons from '../../icons';

export default {
  name: 'ManageDevices',
  components: { DevicesList },
  data() {
    return {
      tab: 'doors',
      interval: null,
      createDialog: false,
      createLoading: false,
      createError: '',
      createForm: { name: '', description: '', ipAddress: '' },
    };
  },
  computed: {
    ...mapGetters('adminTools', ['interlocks', 'doors', 'memberbucksDevices']),
    icons() {
      return icons;
    },
  },
  beforeMount() {
    this.getDoors();
    this.getInterlocks();
    this.getMemberbucksDevices();

    this.interval = setInterval(() => {
      this.getDoors();
      this.getInterlocks();
      this.getMemberbucksDevices();
    }, 30 * 1000);
  },
  beforeUnmount() {
    clearInterval(this.interval);
  },
  methods: {
    ...mapActions('adminTools', [
      'getInterlocks',
      'getDoors',
      'getMemberbucksDevices',
    ]),
    manageDevice(deviceId, deviceTypeStr) {
      this.$q
        .dialog({
          component: DeviceDialog,
          componentProps: {
            test: 'something',
            deviceType: deviceTypeStr,
            deviceId: String(deviceId),
          },
        })
        .onOk(() => undefined)
        .onCancel(() => undefined)
        .onDismiss(() => undefined);
    },
    downloadAccessCsv() {
      const link = document.createElement('a');
      link.href = '/api/admin/interlocks/export-csv/';
      link.download = 'interlock_access.csv';
      link.click();
    },
    openCreateInterlock() {
      this.createForm = { name: '', description: '', ipAddress: '' };
      this.createError = '';
      this.createDialog = true;
    },
    async submitCreateInterlock() {
      if (!this.createForm.name.trim()) {
        this.createError = this.$t('interlocks.name') + ' is required.';
        return;
      }
      this.createLoading = true;
      this.createError = '';
      try {
        await this.$axios.post('/api/admin/interlocks/', this.createForm);
        this.createDialog = false;
        this.$q.notify({ message: this.$t('interlocks.createSuccess') });
        await this.getInterlocks();
      } catch (e) {
        this.createError =
          e.response?.data?.error || this.$t('interlocks.createFail');
      } finally {
        this.createLoading = false;
      }
    },
  },
};
</script>
