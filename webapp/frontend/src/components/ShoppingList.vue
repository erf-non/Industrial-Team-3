<script setup>
import { ref, defineProps, toValue, watch, reactive } from 'vue'

const http_endpoint = "https://ngc8pq0cs8.execute-api.ap-northeast-2.amazonaws.com";
const search_endpoint = `${http_endpoint}/search/products?query=`
const details_endpoint = `${http_endpoint}/product/details?product_id=`;

const props = defineProps(['items'])
const emit = defineEmits(['hasChanged'])

let productSelected = ref({});
let selectOptions = reactive([]);

//const { items } = toRefs(props)
let addItem = () => {
    let product = toValue(productSelected);

    // check if item has empty title or product_id
    if (!product || !product.name_en || !product.product_id) return;
    
    // check for duplicates, don't insert if item alredy exists and increment the count instead
    let found = false;
    props.items.forEach(item => {
      if (item.product_id == product.product_id) {
        item.count++;
        found = true;
      }
    });
    if (found) return;
    
    props.items.unshift({ id: props.items.length + 1, title: product.name_en,
       product_id: product.product_id, done: false, count: 1 });
    
    emit('update:hasChanged', true);
}

// move completed items at the end of the list
watch(() => props.items, (newItems, oldItems) => {
  props.items.sort((a, b) => {
    if (a.done === b.done) {
      return a.id - b.id; // secondary sort by id
    }
    return a.done - b.done;
  });
}, { deep: true });

import { debounce } from 'lodash';

let onSearch = debounce((search, loading) => {
  if (search.length) {
    loading(true);
    fetch(
      search_endpoint + encodeURIComponent(search)
    ).then(res => {
      res.json().then(json => {
        // clear the select array
        selectOptions.splice(0, selectOptions.length);

        json.products.forEach((item) => {
          selectOptions.push(item);
        });
        loading(false);
      });
    });
  }
}, 300);

let increment = (item) => {
  item.count = Math.min(99, item.count + 1);
  emit('update:hasChanged', true);
}

let decrement = (item) => {
  item.count = Math.max(0, item.count - 1);
  emit('update:hasChanged', true);
}

// https://dev.to/pyrsmk/how-to-use-the-contenteditable-attribute-in-vue-3-a89
let validateCount = (event) => {
  // check if number is between 1 and 99 and length is max 2
  let count = parseInt(event.target.innerText);
  if (isNaN(count) || count < 1 || count > 99) {
    if (count > 99) {
      event.target.innerText = 99;
    } else {
      event.target.innerText = 1;
    }
  }

  // find item by id and edit count
  props.items.forEach(item => {
    if (item.id == event.target.dataset.id) {
      item.count = parseInt(event.target.innerText);
      emit('update:hasChanged', true);
      return;
    }
  });
}

let countKeydown = (event) => {
  // listen to arrow up and down keys
  if (event.key === 'ArrowUp') {
    console.log('ArrowUp');
    event.preventDefault();
    
    props.items.forEach(item => {
      if (item.id == event.target.dataset.id) {
        increment(item);
        return;
      }
    });
    return;
  } else if (event.key === 'ArrowDown') {
    console.log('ArrowDown');
    event.preventDefault();

    props.items.forEach(item => {
      if (item.id == event.target.dataset.id) {
        if (item.count == 1) return;
        decrement(item);
        return;
      }
    });
  
    return;
  }

  //if (!isFinite(event.key))
  //  event.target.blur();
}

</script>

<template>
  <div class="container">
    <h2 class="text-center mb-4">Shopping List</h2>
    <BListGroup>
      <TransitionGroup name="list" tag="div">
        <BListGroupItem class="p-0 ps-4 py-1" v-for="item in items" :key="item.id" :class="{ 'item-done': item.done, 'd-flex': true }">
          <BFormCheckbox size="lg" class="d-block" v-model="item.done">
            <div :class="{ 'd-inline': true, 'strike': item.done }">{{ item.title }}</div>
          </BFormCheckbox>
          <BInputGroup>
            <template #prepend>
              <BButton variant="light-subtle" :class="{ 'btn': true, 'btn-outline-success': item.count < 99,
                 'cnt-btn': true, 'disabled': item.count == 99, 'btn-outline-dark': item.count == 99 }" :disabled="item.done" @click="increment(item)">
                <i :class="{ 'bi-plus': item.count < 99, 'bi-ban': item.count == 99 }"></i>
              </BButton>
            </template>
            <span contenteditable spellcheck="false" @blur="validateCount" @keydown="countKeydown" :data-id="item.id" class="num-input">{{ item.count }}</span>
            <!--<BFormInput type="number" min="0" max="99" maxlength="2" :disabled="item.done" v-model="item.count"/> -->
            <template #append>
              <BButton variant="light-subtle" class="btn btn-outline-danger cnt-btn" :disabled="item.done" @click="decrement(item)">
                <i :class="{ 'bi-dash': item.count > 1, 'bi-trash3': item.count == 1 }"></i>
              </BButton>
            </template>
          </BInputGroup>
        </BListGroupItem>
      </TransitionGroup>
    </BListGroup>
    <div class="d-flex">
      <v-select :filterable="false" :options="selectOptions" @search="onSearch" label="name_en" v-model="productSelected" model="product_id" class="item-select py-3">
        <template v-slot:no-options>
          Search and add products...
        </template>
      </v-select>
      <!--<BFormInput v-model="itemText" placeholder="Enter your name" size="lg" class="my-3 flex-shrink-1" /> -->
      <BButton @click="addItem" class="ms-2 my-3 flex-shrink-0">Add Item</BButton>
    </div>
  </div>
</template>

<style>
.num-input {
  padding: 6px;
  text-align: center;
  width: 2.1em;
  border: 1px solid #ced4da;
  overflow: hidden;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.17s ease-out;
}

.item-done {
  color: grey !important;
  text-decoration: line-through;
}

.item-select {
  width: 100%;
  height: 64px;
}

.form-check {
  flex: 1 0 auto;
}

.input-group {
  flex: 0 1 100px;
  align-items: center !important;
  margin-right: 12px;
}

/* Chrome, Safari, Edge, Opera */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
  text-align: center;
  padding: 6px;
}

/* Firefox */
input[type=number] {
  -moz-appearance: textfield;
  text-align: center;
  padding: 6px;
}

.cnt-btn {
  padding: 6px 8px !important;
}

/* ensure leaving items are taken out of layout flow so that moving
   animations can be calculated correctly. */
.list-leave-active {
  position: absolute;
}

.form-check {
  display: flex !important;
  align-items: center;
}

.form-check-label {
  display: block !important;
  padding-left: 12px;
  padding-top: 8px;
  padding-bottom: 8px;
  width: 100%;
}

.form-control-lg {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  padding-right: 0 !important;
}

.vs__search {
  height: 28px;
}

#vs1__listbox {
  transform: translateY(-10px);
  box-shadow: none;
}

.v-select {
  font-size: 110%;
}

/* https://stackoverflow.com/questions/36267507/is-it-possible-to-animate-a-css-line-through-text-decoration */
@keyframes strike{
  0%   { width : 0; }
  100% { width: 100%; }
}
.strike {
  position: relative;
}
.strike::after {
  content: ' ';
  position: absolute;
  top: 50%;
  left: 0;
  width: 100%;
  height: 2.4px;
  background: grey;
  animation-name: strike;
  animation-duration: .8s;
  animation-timing-function: cubic-bezier(.23,1,.32,1);
  animation-iteration-count: 1;
  animation-fill-mode: forwards; 
}
</style>
