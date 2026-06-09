<template>
  <div
    v-if="managedInterlocks.length"
    class="q-mt-lg full-width"
    style="max-width: 800px"
  >
    <q-separator class="q-mb-md" />
    <p class="text-h6">{{ $t('access.trainerPanel') }}</p>
    <p class="text-body2 text-grey-7">{{ $t('access.trainerPanelDesc') }}</p>

    <q-expansion-item
      v-for="interlock in managedInterlocks"
      :key="interlock.id"
      bordered
      class="q-mb-md rounded-borders"
      default-opened
    >
      <template v-slot:header>
        <q-item-section>
          <q-item-label>{{ interlock.name }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-badge color="blue">{{ $t('access.roleTrainer') }}</q-badge>
        </q-item-section>
      </template>

      <q-card>
        <q-card-section>
          <!-- Authorised members section -->
          <div>
            <div class="row items-center q-mb-sm">
              <div class="text-subtitle2 col">
                {{ $t('access.roleUser') }} Members
              </div>
              <q-btn
                flat
                dense
                color="positive"
                :label="$t('access.grantAccess')"
                icon="mdi-plus"
                @click="openAssign(interlock)"
              />
            </div>
            <q-list bordered separator>
              <q-item v-if="!interlock.users.length">
                <q-item-section class="text-grey-6 text-caption">
                  {{ $t('access.noMembersWithAccess') }}
                </q-item-section>
              </q-item>
              <q-item v-for="u in interlock.users" :key="u.userId">
                <q-item-section avatar>
                  <q-icon name="mdi-account" color="positive" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ u.name }}</q-item-label>
                  <q-item-label v-if="u.grantedBy" caption>
                    {{ $t('access.grantedBy', { name: u.grantedBy }) }}
                    {{ formatDate(u.grantedDate, false) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    flat
                    dense
                    round
                    icon="mdi-account-remove"
                    color="negative"
                    @click="revokeAccess(interlock, u.userId)"
                  >
                    <q-tooltip>{{ $t('access.revokeAccess') }}</q-tooltip>
                  </q-btn>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>
      </q-card>
    </q-expansion-item>

    <!-- Member search dialog -->
    <q-dialog v-model="assignDialog">
      <q-card style="min-width: 350px">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ $t('access.grantAccess') }}</div>
          <q-space />
          <q-btn icon="mdi-close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <q-select
            v-model="selectedMember"
            use-input
            clearable
            outlined
            :label="$t('access.searchMembers')"
            :options="memberOptions"
            option-label="name"
            option-value="id"
            @filter="searchMembers"
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.name }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.email }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  Type to search members
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="$t('button.cancel')" v-close-popup />
          <q-btn
            :label="$t('access.grantAccess')"
            color="primary"
            :disable="!selectedMember"
            @click="confirmAssign"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import { formatDate } from '@mixins/formatMixin';

export default {
  name: 'InterlockManagePanel',

  data() {
    return {
      managedInterlocks: [],
      assignDialog: false,
      assignInterlock: null,
      selectedMember: null,
      memberOptions: [],
    };
  },

  mounted() {
    this.loadManagedInterlocks();
  },

  methods: {
    formatDate,

    loadManagedInterlocks() {
      this.$axios
        .get('/api/access/interlocks/managed/')
        .then((response) => {
          this.managedInterlocks = response.data;
        })
        .catch(() => undefined);
    },

    openAssign(interlock) {
      this.assignInterlock = interlock;
      this.selectedMember = null;
      this.memberOptions = [];
      this.assignDialog = true;
    },

    searchMembers(val, update) {
      if (val.length < 2) {
        update(() => {
          this.memberOptions = [];
        });
        return;
      }
      this.$axios
        .get('/api/access/members/search/', { params: { q: val } })
        .then((response) => {
          update(() => {
            this.memberOptions = response.data;
          });
        })
        .catch(() => {
          update(() => {
            this.memberOptions = [];
          });
        });
    },

    confirmAssign() {
      const interlock = this.assignInterlock;
      const userId = this.selectedMember.id;
      this.$axios
        .put(`/api/access/interlocks/${interlock.id}/authorise/${userId}/`)
        .then(() => {
          this.assignDialog = false;
          this.loadManagedInterlocks();
        })
        .catch(() => {
          this.$q.dialog({
            title: this.$t('error.error'),
            message: this.$t('error.requestFailed'),
          });
        });
    },

    revokeAccess(interlock, userId) {
      this.$axios
        .put(`/api/access/interlocks/${interlock.id}/revoke/${userId}/`)
        .then(() => this.loadManagedInterlocks())
        .catch(() => {
          this.$q.dialog({
            title: this.$t('error.error'),
            message: this.$t('error.requestFailed'),
          });
        });
    },
  },
};
</script>
