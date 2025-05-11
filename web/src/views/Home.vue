<script setup>
  /*import HelloWorld from './components/HelloWorld.vue'
  import TheWelcome from './components/TheWelcome.vue'*/
import {ref} from "vue";
import { useRouter, useRoute } from 'vue-router'
const router = useRouter()

const count = ref();
const submit = () => {
  router.push({name: 'batch-record', params:{count: count.value.toString()}});
}
const criminal_record_count = () => {

}
</script>

<template>
  <router-view>
    <div class="text-center" style="text-align: -moz-center">
      <a href="https://easyproonline.com/" target="_blank" class="text-center" id="easypro-link">
        <img src="./../assets/easypro_logo.png" id="easypro-logo" class="logo vue" alt="Easypro logo" width="100" height="100"/>
      </a>
      <h1 class="font-bold sm:text-5xl lg:text-6xl text-3xl leading-snug lg:leading-tight">Single payment ... <br>Multiple criminal records</h1>
      <p class="mt-8 lg:text-lg md:text-xl/6 sm:text-xl/5 font-medium text-pretty text-gray-500 ">Help your relatives to get their criminal records in few days by submitting all requests in one time.</p>

      <form @submit.stop.prevent="submit" class="mt-14 mb-32 gap-x-4">
  <!--    <form @submit.stop.prevent="submit" class="mt-6 mb-32 max-w-md gap-x-4" style="display: inline-flex">-->
        <label for="email-address" class="block font-medium text-gray-800 text-left mb-1">Requests count :</label>
        <input id="email-address" name="count" v-model="count" @submit="submit();" type="number" autocomplete="number" required
               class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="2"
               min="2"/>
        <button type="submit" class="rounded-md bg-green-500 px-3.5 py-2.5 float-right lg:w-44 sm:w-40 w-full h-14
         text-sm font-semibold text-white shadow-xs hover:bg-green-400 focus-visible:outline-2
         focus-visible:outline-offset-2 focus-visible:outline-green-500">Continue</button>
      </form>
      <div style="margin: 0 auto">
        <p class="mt-2 text-gray-500 text-center">© 2025 <a href="#" class=" inline-block mt-1 m text-lg anchor-green-500 hover:anchor-green-700 leading-tight font-medium te xt-black hover:underline">EASYPRO EIG</a> All rights reserved.</p>
      </div>
    </div>
  </router-view>
</template>

<style scoped>
header {
  line-height: 1.5;
}
a:hover {
  text-decoration: none;
}
#easypro-link:hover {
  background: none;
}
.logo {
  display: block;
  margin: 0 auto 2rem;
  will-change: filter;
  transition: filter 300ms;
}

/*.logo {
  height: 6em;
  padding: 1.5em;

}*/
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
.top-model:hover {
  filter: drop-shadow(0 0 2em #15803DFF);
}

#easypro-logo {
  text-align: center;
  margin: auto;
  float: none
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
