<script setup>
import { ref, defineProps, toValue, watch, reactive } from 'vue'

const http_endpoint = "https://ngc8pq0cs8.execute-api.ap-northeast-2.amazonaws.com";
const details_endpoint = `${http_endpoint}/product/details?product_id=`;

const props = defineProps(['basketItems', 'basketTotal'])
let productDetailsMap = reactive({});

watch(() => props.basketItems, (newItems, oldItems) => {
  console.log('BasketItems changed', newItems);
  newItems.forEach(item => {
    fetchProductDetails(item);
  });
},  { deep: true });

let fetchProductDetails = async (product_id) => {
  if (productDetailsMap[product_id]) return;
  let response = await fetch(details_endpoint + product_id);
  let json = await response.json();
  productDetailsMap[product_id] = json;
}

let getProductDetails = (product_id) => {
  if (productDetailsMap[product_id]) {
    return productDetailsMap[product_id];
  } else {
    return { name_en: 'Loading...' };
  }
}

let isProductDetailLoaded = (product_id) => {
  return productDetailsMap[product_id] !== undefined;
}

</script>

<template>
  <div class="container mt-4 ">
    <h2 class="text-center mb-4">Basket Contents <BBadge variant="dark" class="ms-2" v-if="basketTotal">${{ basketTotal }}</BBadge></h2>
    <BListGroup>
      <TransitionGroup name="list" tag="div">
        <BListGroupItem class="" v-for="itemId in basketItems" :key="itemId" :class="{ 'd-flex': true }">
            <div class="basket-item d-flex justify-content-between align-items-center w-100">
              <span v-if="isProductDetailLoaded(itemId)">{{ getProductDetails(itemId)["ProductNameEN"] }}</span> <!--{{ getProductDetails(itemId)["ProductNameEN"] }} -->
              <span class="loading-placeholder" v-else><div class="animated-background"></div></span>
              <BBadge v-if="isProductDetailLoaded(itemId)" variant="dark">${{ getProductDetails(itemId)["Price"] }}</BBadge>
            </div>
        </BListGroupItem>
      </TransitionGroup>
    </BListGroup>
  </div>
</template>

<style>
.basket-item {
  font-size: 120%;
}

/* https://codepen.io/aji/pen/evMKWN */
.loading-placeholder {
 margin: 0 auto;
 min-width: 200px;
 max-width: 400px;
 display: block;
 min-height: 1.5em;
 background-color: #eee;
}

@keyframes placeHolderShimmer{
    0%{
        background-position: -468px 0
    }
    100%{
        background-position: 468px 0
    }
}

.animated-background {
    animation-duration: 1.25s;
    animation-fill-mode: forwards;
    animation-iteration-count: infinite;
    animation-name: placeHolderShimmer;
    animation-timing-function: linear;
    background: darkgray;
    background: linear-gradient(to right, #eeeeee 10%, #dddddd 18%, #eeeeee 33%);
    background-size: 800px 104px;
    height: 1.5em;
    position: relative;
}
</style>
