<template>
  <q-page class="column flex content-center justify-start">
    <div class="column full-width items-center q-pa-md">
      <interlock-manage-panel />
    </div>
  </q-page>
</template>

<script>
import InterlockManagePanel from '@components/InterlockManagePanel.vue';

export default {
  name: 'ManageInterlocks',
  components: { InterlockManagePanel },
};
</script>
