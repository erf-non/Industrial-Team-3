<script setup>
import { reactive } from 'vue';
import { watch, ref, onMounted } from 'vue';

const wsEndpoint = "wss://917jdxtwp1.execute-api.ap-northeast-2.amazonaws.com/production?sess=b45887be0ba31546";


let listPublicId = '430739fc79708a49';
let listPrivateId = '0957bb8e39fd562baa48243fbff95282';
let wsConnection = null;

let wsConnected = ref(false);
let listRetrieved = ref(false);
let hasChanged = ref(false);

let items = reactive([]);

// listen for changes in the items array and log them
watch(() => items, (newItems, oldItems) => {
  // items with count 0, remove them from the list
  items.forEach((item, index) => {
    if (item.count === 0) {
      items.splice(index, 1);
    }
  });
}, { deep: true });

// connect to websocket on mount and listen for messages

onMounted(() => {
  let reconnectInterval = null;
  wsConnection = new WebSocket(wsEndpoint);
  wsConnection.onopen = () => {
    console.log('connected');
    wsConnected.value = true;
    wsConnection.send(JSON.stringify({
      'action': 'get_list', 'body': {'public_id': listPublicId}
    }));
  };
  wsConnection.onclose = () => {
    console.log('connection closed');
    wsConnected.value = false;
    // try to reconnect here
    reconnectInterval = setInterval(() => {
      wsConnection = new WebSocket(wsEndpoint);
      wsConnection.onopen = () => {
        console.log('reconnected');
        wsConnected.value = true;
        clearInterval(reconnectInterval);
        reconnectInterval = null;
      };
    }, 3000); // wait for 3 seconds before reconnecting
  };

  wsConnection.onmessage = (event) => {
    console.log('message received:', event.data);
    const message = JSON.parse(event.data);
    if (message.event === 'add_product') {
      const productId = message.product_id;
      items.forEach(item => { if (item.product_id === productId) { item.done = true; } });
    } else if (message.event === 'update_list' && message.success === true) {
      hasChanged.value = false;
    } else if (message.event === 'get_list') {
      // clear the items array and add the new items
      items.splice(0, items.length);
      message.items.forEach(item => {
        items.push(item);
      });
      listRetrieved.value = true;
    }
  };

  setInterval(() => {
    console.log('checking for changes', hasChanged.value);

    if (hasChanged.value) {
      if (wsConnection.readyState !== WebSocket.OPEN) {
        console.log('connection not open, skipping');
        return;
      }

      wsConnection.send(JSON.stringify({
        'action': 'update_list', 'body': {'public_id': listPublicId, 'private_id': listPrivateId, 'items': items}
      }))
    }
  }, 1000);
});
</script>

<template>
<BNavbar toggleable="lg" v-b-color-mode="'light'" class="pt-0">
  <div class="container d-flex py-3" >
    <div class="d-flex">
        <BNavbarBrand href="#">Basket</BNavbarBrand>
        <BNavbarToggle target="nav-collapse"/>
    </div>
  <BCollapse id="nav-collapse" is-nav>
    <!-- Right aligned nav items -->
    <BNavbarNav class="ms-auto mb-2 mb-lg-0">
      <BNavItem v-show="wsConnected"><span class="badge rounded-pill text-bg-success connected">Connected</span></BNavItem>
      <!--
      <BNavItem href="#">Link</BNavItem>
      <BNavItemDropdown text="Lang" right>
        <BDropdownItem href="#">EN</BDropdownItem>
        <BDropdownItem href="#">ZH</BDropdownItem>
      </BNavItemDropdown>
  -->

    </BNavbarNav>
  </BCollapse>  
  </div>
</BNavbar>
<div>
<Transition>
  <div v-if="wsConnected && listRetrieved" key="list">
    <ShoppingList :items="items" v-model:hasChanged="hasChanged"/>
  </div>
  <div v-else key="loader" class="loader">
    <div class="container">
      <div class="alert alert-danger" v-if="listRetrieved">Connection lost. Please wait...</div>
      <div class="d-flex justify-content-center" v-else>
        <BSpinner />
      </div>
    </div>
  </div>
</Transition>
</div>
</template>

<style>
.loader {
  position: absolute;
  width: 100%;
  margin: auto;
}

.v-enter-active,
.v-leave-active {
  transition: all 0.4s cubic-bezier(.25,1.01,.32,1);
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}

header {
  line-height: 1.5;
}


.logo {
  display: block;
  margin: 0 auto 2rem;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>
