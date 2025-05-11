<script setup>
  import { PhotoIcon, UserCircleIcon } from '@heroicons/vue/24/solid'
  import { ChevronDownIcon } from '@heroicons/vue/16/solid'
  import { useRoute } from 'vue-router';
  import axios from 'axios';
  import {FwbButton, FwbImg, FwbModal} from 'flowbite-vue'
  import { useToast } from "vue-toastification";
  import Toast from "vue-toastification";
  import "vue-toastification/dist/index.css";
  import { ref, onMounted } from "vue";
  const rootUrl = 'http://127.0.0.1:8000';
  const region = ref('');
  const maritalStatus = ref('SINGLE');
  const route = useRoute()  // Get the current route object
  const count = route.params.count  // Access the 'count' parameter
  const countries = ref([])
  const courtBirthCode = ref(   '')
  const countryResidencyCode = ref('CM')
  const countryBirthCode = ref('CM')
  const nationalityCode = ref('CM')
  const courts = ref([])
  const departmentBirthList = ref([])
  const departmentResidencyList = ref([])
  const departmentBirth = ref('Moungo');
  const departmentResidency = ref('Moungo');
  const regionBirthCode = ref('LT');
  const regionResidencyCode = ref('LT');
  const municipalityResidency = ref('');
  const browserLanguage = ref('');
  const municipalities = ref([]);
  const submitted = ref(false);
  const hasRegistered = ref(false);
  const hasChoosePaymentMethod = ref(false);
  const totalAmount = ref(0);
  const criminalRecordIDs = ref("");
  const isShowModal = ref(false);
  const paymentMethod = ref('')
  const fullLanguage = navigator.language || navigator.userLanguage;
  browserLanguage.value = fullLanguage.split('-')[0].toString();

  const toast = useToast();
  toast.success("Request created successfully!");
  const getCountries = () => {
    axios.get(rootUrl + '/countries', {params: {'lang': browserLanguage.value}}).then(response => {
      // countries.value = response.data["results"];
      countries.value = response.data;
    });
  };
  const updateDepartmentBirthList = (regionCode) => {
    axios.get(rootUrl + '/departments', {params: {'region_code': regionCode}}).then(response => {
      departmentBirthList.value = response.data
      departmentBirth.value = departmentBirthList.value[0]
    });
  };
  const updateDepartmentResidencyList = (regionCode) => {
    axios.get(rootUrl + '/departments', {params: {'region_code': regionCode}}).then(response => {
      departmentResidencyList.value = response.data
      departmentResidency.value = departmentResidencyList.value[0]
    })
  }
  const updateCourtBirthList = (department) => {
    axios.get(rootUrl + '/courts', {params: {'department_id': department}}).then(response => {
      courts.value = response.data;
    })
  }
  const updateMunicipalityList = (department) => {
    axios.get(rootUrl + '/municipalities', {params: {'department_name': department}}).then(response => {
      municipalities.value = response.data;
      municipalityResidency.value = municipalities.value[0]
    })
  }
  const counter = ref(1);
  const form = ref();
  const resetForm = () => {
    maritalStatus.value = 'SINGLE'
    countries.value = []
    courtBirthCode.value = ''
    countryResidencyCode.value = 'CM'
    countryBirthCode.value = 'CM'
    nationalityCode.value = 'CM'
    courts.value = []
    departmentBirthList.value = []
    departmentResidencyList.value = []
    departmentBirth.value = 'Moungo'
    departmentResidency.value = 'Moungo'
    regionBirthCode.value = 'LT'
    regionResidencyCode.value = 'LT'
    municipalityResidency.value = ''
    municipalities.value = []
    getCountries();
    updateDepartmentResidencyList(regionResidencyCode.value)
    updateDepartmentBirthList(regionResidencyCode.value)
    updateCourtBirthList(departmentBirth.value)
    updateMunicipalityList(departmentBirth.value)
  }
  resetForm();
  const upload = (inputID, mediaField) => {
    const inputElement = document.getElementById('' + inputID);
    const formData = new FormData();
    formData.append("file", inputElement.files[0], inputElement.files[0].name)
    formData.append('model_name', "request.request");
    formData.append('media_field', mediaField);
    axios.post(rootUrl + '/upload_file/?upload_hash=david',
        formData,
        {headers: {'Content-Type': 'multipart/form-data'}})
        .then((response) => {
          const divPreview = document.getElementById(inputID + '-preview');
          divPreview.classList.remove('hidden');
          divPreview.classList.add('flex');
          divPreview.style.backgroundImage = "url(" + rootUrl +  response.data.preview + ")";
          console.log(mediaField + '_url');
          inputElement.classList.add('hidden');
          const selector = mediaField + "_url"
          document.querySelector(`[name=${selector}]`).value = rootUrl + response.data.url;
        });
  }
  const submitAllCriminalRecords = () => {
    showModal();
    const formElement = document.getElementById('modal-form');
    const formData = new FormData(formElement);
      // Convert to plain object (optional)
    const data = Object.fromEntries(formData.entries());
    data['request_code_ids'] = criminalRecordIDs
    axios.post(rootUrl + '/api/payment/checkout/', data, {headers: {'Content-Type': 'multipart/form-data'}})
    .then((response) => {
      console.log(response.data)
      console.log(criminalRecordIDs.value, totalAmount.value);
      toast.success("Request " + response.data.request.code + "created successfully!", {position: 'top-center', icon: true, closeOnClick: true, timeout: 5000});
    });
  }
  const saveCriminalRecord = () => {
    document.getElementById("save").classList.add('cursor-not-allowed');
    submitted.value = true;
    if (counter.value <= parseInt(count)){
      counter.value += 1;
      const formElement = document.getElementById('form');
      const formData = new FormData(formElement);
      // Convert to plain object (optional)
      const data = Object.fromEntries(formData.entries());
      // You can now send it somewhere:
      axios.post(rootUrl + '/requests/', data, {headers: {'Content-Type': 'multipart/form-data'}})
          .then((response) => {
            resetForm();
            submitted.value = false;
            setTimeout(() => {
              hasRegistered.value = true;
            }, 2000);
            criminalRecordIDs.value += response.data.request.code + ",";
            totalAmount.value += response.data.request.amount;
            console.log(criminalRecordIDs.value)
            console.log(totalAmount.value)
            toast.success("Request " + response.data.request.code + "created successfully!");
                // {position: "top-center", icon: true, closeOnClick: true, timeout: 5000});
          });
    } else {
      submitAllCriminalRecords()
    }
  };
  const showMobileMoneyForm = (method) => {
    if (method === 'mtn') {
      paymentMethod.value = 'mtn-momo';
      document.getElementById('modal-header').innerHTML = 'Pay with MTN Mobile Money';
    } else {
      paymentMethod.value = 'orange-money';
      document.getElementById('modal-header').innerHTML = 'Pay with Orange Money';
    }
  }
  const closeModal = () => {
    isShowModal.value = false
  }
  const showModal = () => {
    isShowModal.value = true
  }
  defineExpose({
    counter,
    resetForm,
    submitAllCriminalRecords
  });
</script>

<template>

  <fwb-modal v-if="isShowModal" @close="closeModal" position="top-center" persistent>
    <template #header>
      <div class="flex items-center text-lg" id="modal-header">
        Choose payment methods
      </div>
    </template>
    <template #body>
      <fwb-img v-if="!hasChoosePaymentMethod" @click="showMobileMoneyForm('mtn')" src="" class="w-64"/>
      <fwb-img v-if="!hasChoosePaymentMethod" @click="showMobileMoneyForm('orange')" src="" class="w-64"/>
      <form v-if="hasChoosePaymentMethod" id="modal-form">
        <div class="sm:col-span-3 ">
          <label for="amount" class="block text-sm/6 font-medium text-gray-900">Amount:</label>
          <div class="mt-2">
            <div class="absolute items-center ps-3.5 pointer-events-none">
              <svg class="w-5 h-5 mt-4 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 19 18">
                <path d="M18 13.446a3.02 3.02 0 0 0-.946-1.985l-1.4-1.4a3.054 3.054 0 0 0-4.218 0l-.7.7a.983.983 0 0 1-1.39 0l-2.1-2.1a.983.983 0 0 1 0-1.389l.7-.7a2.98 2.98 0 0 0 0-4.217l-1.4-1.4a2.824 2.824 0 0 0-4.218 0c-3.619 3.619-3 8.229 1.752 12.979C6.785 16.639 9.45 18 11.912 18a7.175 7.175 0 0 0 5.139-2.325A2.9 2.9 0 0 0 18 13.446Z"/>
              </svg>
            </div>
            <input required id="amount" name="amount" type="number" autocomplete="off" class="w-full block
            min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
             drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
              placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
               focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" value="{{totalAmount.value}}" readonly disabled/>
          </div>
        </div>
        <div class="sm:col-span-3 ">
          <label for="phone" class="block text-sm/6 font-medium text-gray-900">Phone <span style="color: red;">* </span>:</label>
          <div class="mt-2">
            <div class="absolute items-center ps-3.5 pointer-events-none">
              <svg class="w-5 h-5 mt-4 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 19 18">
                <path d="M18 13.446a3.02 3.02 0 0 0-.946-1.985l-1.4-1.4a3.054 3.054 0 0 0-4.218 0l-.7.7a.983.983 0 0 1-1.39 0l-2.1-2.1a.983.983 0 0 1 0-1.389l.7-.7a2.98 2.98 0 0 0 0-4.217l-1.4-1.4a2.824 2.824 0 0 0-4.218 0c-3.619 3.619-3 8.229 1.752 12.979C6.785 16.639 9.45 18 11.912 18a7.175 7.175 0 0 0 5.139-2.325A2.9 2.9 0 0 0 18 13.446Z"/>
              </svg>
            </div>
            <input required id="phone" name="phone" type="number" autocomplete="off" class="w-full block
            min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
             drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
              placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
               focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" />
          </div>
        </div>
        <input type="hidden" name="payment_method" v-if="paymentMethod.value === 'mtn'" value="mtn-momo">
        <input type="hidden" name="payment_method" v-if="paymentMethod.value === 'orange'" value="orange-money">
      </form>
<!--      <p class="text-base leading-relaxed text-gray-500 dark:text-gray-400">-->
<!--        Request of {{criminalRecordIDList[counter.value]}} has created successfully.-->
<!--      </p>-->
<!--      <p class="text-base leading-relaxed text-gray-500 dark:text-gray-400">-->
<!--        The European Union’s General Data Protection Regulation (G.D.P.R.) goes into effect on May 25 and is meant to ensure a common set of data rights in the European Union. It requires organizations to notify users as soon as possible of high-risk data breaches that could personally affect them.-->
<!--      </p>-->
    </template>
    <template #footer v-if="hasChoosePaymentMethod">
      <div class="flex justify-between">
<!--        <fwb-button @click="closeModal" color="alternative">-->
<!--          Decline-->
<!--        </fwb-button>-->
        <fwb-button @click="closeModal" color="green">
          Continue
        </fwb-button>
      </div>
    </template>
  </fwb-modal>

  <h1 class="font-bold sm:text-5xl lg:text-6xl text-3xl leading-snug lg:leading-tight text-center mt-9 mb-9">Save user {{ counter }}</h1>
  <form @submit.prevent="saveCriminalRecord" ref="form" id="form">
    <div class="space-y-12">
      <div class="border-b border-gray-900/10 pb-12 ">
        <h2 class="text-base/7 font-semibold text-gray-900">Personal Information</h2>
        <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
          <div class="sm:col-span-1">
            <label for="first-name" class="block text-sm/6 font-medium text-gray-900">Civility <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="civility" name="user_civility" class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option>Sir</option>
                <option>Mrs</option>
                <option>Ms</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-4">
            <label for="first-name" class="block text-sm/6 font-medium text-gray-900">First name <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <input required type="text" name="user_first_name" id="first-name" placeholder="John" autocomplete="off" class="w-full
               block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" />
            </div>
          </div>
          <div class="sm:col-span-4">
            <label for="last-name" class="block text-sm/6 font-medium text-gray-900">Last name <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <input required type="text" name="user_last_name" id="last-name" placeholder="Doe" autocomplete="off"
                     class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" />
            </div>
          </div>
          <div class="sm:col-span-9">
            <label for="profession" class="block text-sm/6 font-medium text-gray-900">Profession <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <input required id="profession" name="user_occupation" type="text" autocomplete="off" class="w-full block
              min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="Software Engineer"/>
            </div>
          </div>
          <div class="sm:col-span-9">
            <label for="marital-status" class="block text-sm/6 font-medium text-gray-900">Marital status <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="marital-status" v-model="maritalStatus" autocomplete="off"
                      name="user_marital_status" class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4
                      py-5 text-base peer/email drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1
                       -outline-offset-1 outline-gray-300 placeholder:text-gray-600 focus:outline focus:outline-2
                        focus:-outline-offset-2 focus:ring-green-600 focus:shadow-none focus:drop-shadow-none
                         focus:outline-green-600 border-slate-300">
                <option value="SINGLE">Single</option>
                <option value="MARRIED">Married</option>
                <option value="DIVORCED">Divorced</option>
                <option value="WIDOW">Widow</option>
                <option value="WIDOWER">Widower</option>
              </select>
            </div>
          </div>
          <div class="col-span-9" v-if="maritalStatus !== 'SINGLE'">
            <label for="marital-certificate" v-if="maritalStatus === 'MARRIED' || maritalStatus === 'WIDOW' || maritalStatus === 'WIDOWER'" class="block text-sm/6 font-medium text-gray-900">Marital certificate <span style="color: red;">* </span>:</label>
            <label for="marital-certificate" v-if="maritalStatus === 'DIVORCED'" class="block text-sm/6 font-medium text-gray-900">Divorce certificate <span style="color: red;">* </span>:</label>
            <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
              <div class="text-center">
                <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                <div class="mt-4 flex text-sm/6 text-gray-600">
                    <label for="marital-certificate" class="relative cursor-pointer rounded-md bg-white font-semibold
                     text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2
                     focus-within:outline-hidden hover:text-indigo-500">
                      <span>Upload a file</span>
                      <input required id="marital-certificate" name="file"
                             @drag="upload('marital-certificate', 'user_wedding_certificate')" @change="upload('marital-certificate', 'user_wedding_certificate')"
                             type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                     <span style="color: red;">* </span>:</label>
                    <p class="pl-1">or drag and drop</p>
                  </div>
                <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
              </div>
            </div>
            <div id="marital-certificate-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_wedding_certificate_url" value=""/>
          </div>
          <div class="sm:col-span-3 ">
          <label for="phone" class="block text-sm/6 font-medium text-gray-900">Phone <span style="color: red;">* </span>:</label>
          <div class="mt-2">
            <div class="absolute items-center ps-3.5 pointer-events-none">
              <svg class="w-5 h-5 mt-4 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 19 18">
                <path d="M18 13.446a3.02 3.02 0 0 0-.946-1.985l-1.4-1.4a3.054 3.054 0 0 0-4.218 0l-.7.7a.983.983 0 0 1-1.39 0l-2.1-2.1a.983.983 0 0 1 0-1.389l.7-.7a2.98 2.98 0 0 0 0-4.217l-1.4-1.4a2.824 2.824 0 0 0-4.218 0c-3.619 3.619-3 8.229 1.752 12.979C6.785 16.639 9.45 18 11.912 18a7.175 7.175 0 0 0 5.139-2.325A2.9 2.9 0 0 0 18 13.446Z"/>
              </svg>
            </div>
            <input required id="phone" name="user_phone_number_1" type="number" autocomplete="off" class="w-full block
            min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
             drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
              placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
               focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" />
          </div>
          </div>
          <div class="sm:col-span-3 ">
            <label for="email" class="block text-sm/6 font-medium text-gray-900">Whatsapp contact <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <div class="absolute items-center ps-3.5 pointer-events-none">
                  <svg class="w-6 h-6 mt-4 text-gray-500 dark:text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 448 512">
                    <path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7 .9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z" />
                  </svg>
              </div>
              <input required id="email" name="user_whatsapp_number" type="number" autocomplete="off" class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" />
            </div>
          </div>
          <div class="sm:col-span-3">
              <label for="email" class="block text-sm/6 font-medium text-gray-900">Email address <span style="color: red;">* </span>:</label>
              <div class="mt-2">
                <div class="absolute items-center ps-3.5 pointer-events-none">
                  <svg class="w-6 h-6 mt-4 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 16">
                    <path d="m10.036 8.278 9.258-7.79A1.979 1.979 0 0 0 18 0H2A1.987 1.987 0 0 0 .641.541l9.395 7.737Z"/>
                    <path d="M11.241 9.817c-.36.275-.801.425-1.255.427-.428 0-.845-.138-1.187-.395L0 2.6V14a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V2.5l-8.759 7.317Z"/>
                  </svg>
                </div>
                <input required id="email" name="user_email" type="email" autocomplete="off" class="w-full block min-w-0 mb-6
                rounded-md bg-white/5 sm:text-sm/6 px-4 py-4 text-base peer/email
                 drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                  placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                   focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" placeholder="sample@easyproonline.com"/>
                <p class="text-sm/6 text-gray-600">Use a permanent address where you can receive mail.</p>
              </div>
            </div>

          <div class="sm:col-span-9">
            <label for="nationality" class="block text-sm/6 font-medium text-gray-900">Nationality <span style="color: red;">* </span>:</label>
            <div class="mt-2 grid grid-cols-1">
              <select id="nationality"  name="user_nationality_code" v-model="nationalityCode" class="w-full block min-w-0
              mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="country in countries" :key="country.iso2" :value="country.iso2">{{country.name}}</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-9">
            <div class="col-span-full">
              <label for="id-card-1" class="block text-sm/6 font-medium text-gray-900">ID Card (recto)<span style="color: red;">* </span>:</label>
              <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
                <div class="text-center">
                  <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                  <div class="mt-4 flex text-sm/6 text-gray-600">
                    <label for="id-card-1" class="relative cursor-pointer rounded-md bg-white font-semibold
                     text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2
                     focus-within:outline-hidden hover:text-indigo-500">
                      <span>Upload a file</span>
                      <input required id="id-card-1" name="file"
                             @drag="upload('id-card-1', 'user_id_card_1')" @change="upload('id-card-1', 'user_id_card_1')"
                             type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                     <span style="color: red;">* </span>:</label>
                    <p class="pl-1">or drag and drop</p>
                  </div>
                  <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
                </div>
              </div>
            </div>
            <div id="id-card-1-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_id_card_1_url" value=""/>
            <div class="col-span-full mt-4">
              <label for="id-card-2" class="block text-sm/6 font-medium text-gray-900">ID Card (verso) <span style="color: red;">* </span>:</label>
              <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
                <div class="text-center">
                  <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                  <div class="mt-4 flex text-sm/6 text-gray-600">
                    <label for="id-card-2" class="relative cursor-pointer rounded-md bg-white font-semibold
                     text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2
                     focus-within:outline-hidden hover:text-indigo-500">
                      <span>Upload a file</span>
                      <input required id="id-card-2"
                             @drag="upload('id-card-2', 'user_id_card_2')" @change="upload('id-card-2', 'user_id_card_2')"
                             name="file" type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                     <span style="color: red;">* </span>:</label>
                    <p class="pl-1">or drag and drop</p>
                  </div>
                  <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
                </div>
              </div>
            </div>
            <div id="id-card-2-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_id_card_2_url" value="" />
          </div>
          <div class="sm:col-span-9">
            <div class="col-span-full">
              <label for="passport-recto" class="block text-sm/6 font-medium text-gray-900">Passport (recto) :</label>
              <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
                <div class="text-center">
                  <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                  <div class="mt-4 flex text-sm/6 text-gray-600">
                    <label for="passport-recto" class="relative cursor-pointer rounded-md bg-white font-semibold
                    text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2
                    focus-within:outline-hidden hover:text-indigo-500">
                      <span>Upload a file</span>
                      <input id="passport-recto"
                             @drag="upload('passport-recto', 'user_passport_1')" @change="upload('passport-recto', 'user_passport_1')"
                             name="file" type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                     <span style="color: red;">* </span>:</label>
                    <p class="pl-1">or drag and drop</p>
                  </div>
                  <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
                </div>
              </div>
            </div>
            <div id="passport-recto-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_passport_1_url" value="" />
            <div class="col-span-full mt-4">
              <label for="passport-verso" class="block text-sm/6 font-medium text-gray-900">Passport (verso) :</label>
              <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
                <div class="text-center">
                  <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                  <div class="mt-4 flex text-sm/6 text-gray-600">
                    <label for="passport-verso" class="relative cursor-pointer rounded-md bg-white font-semibold
                    text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2
                    focus-within:outline-hidden hover:text-indigo-500">
                      <span>Upload a file</span>
                      <input @drag="upload('passport-verso', 'user_passport_2')"
                             @change="upload('passport-verso', 'user_passport_2')"
                             id="passport-verso"  name="file" type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                     <span style="color: red;">* </span>:</label>
                    <p class="pl-1">or drag and drop</p>
                  </div>
                  <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
                </div>
              </div>
              <div id="passport-verso-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_passport_2_url" value="" />
            </div>
          </div>
        </div>
      </div>
      <div class="border-b border-gray-900/10 pb-12">
        <h2 class="text-base/7 font-semibold text-gray-900">Birth information</h2>
        <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-12">
          <div v-bind:class="[countryBirthCode === 'CM' ? 'sm:col-span-3': 'sm:col-span-6']">
            <label for="marital-status" class="block text-sm/6 font-medium text-gray-900">Country of birth <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="country-birth"  name="user_cob_code"  v-model="countryBirthCode" class="w-full block min-w-0 mb-6
               rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="country in countries" :key="country.iso2" :value="country.iso2" >{{country.name}}</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-3" v-show="countryBirthCode === 'CM' ">
            <label for="region-birth" class="block text-sm/6 font-medium text-gray-900">Region of birth <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="region-birth" v-model="regionBirthCode" @change="updateDepartmentBirthList(regionBirthCode)" name="" class="w-full block min-w-0
              mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option value="LT">Littoral</option>
                <option value="OU">West</option>
                <option value="NO">North</option>
                <option value="EN">Far North</option>
                <option value="ES">Centre</option>
                <option value="SU">Sud</option>
                <option value="NW">North-West</option>
                <option value="SW">Sud-West</option>
                <option value="AD">Adamawa</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-3" v-show="countryBirthCode === 'CM' ">
            <label for="department-birth" class="block text-sm/6 font-medium text-gray-900">Department of birth <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="department-birth" name="user_dpb" @change="updateCourtBirthList(departmentBirth)"
                      v-model="departmentBirth" class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6
                      px-4 py-5 text-base peer/email drop-shadow-none shadow-none bg-white text-gray-900 outline
                      outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-600 focus:outline
                      focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="department in departmentBirthList" :key="department.id"
                        :value="department.id">{{department.name}}</option>
              </select>
            </div>
          </div>
          <div v-bind:class="[countryBirthCode === 'CM' ? 'sm:col-span-3': 'sm:col-span-6']">
            <label for="department-birth" class="block text-sm/6 font-medium text-gray-900">Court <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="court-birth" v-model="courtBirthCode" name="court"
                      class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="court in courts" :key="court.id" :value="court.id">{{court.full_name}}</option>
              </select>
            </div>
          </div>
          <div class="col-span-full">
            <label for="birthday-certificate" class="block text-sm/6 font-medium text-gray-900">Birthday certificate <span style="color: red;">* </span>:</label>
            <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
              <div class="text-center">
                <PhotoIcon class="mx-auto size-12 text-gray-300" aria-hidden="true" />
                <div class="mt-4 flex text-sm/6 text-gray-600">
                  <label for="birthday-certificate" class="relative cursor-pointer rounded-md bg-white
                  font-semibold text-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600
                  focus-within:ring-offset-2 focus-within:outline-hidden hover:text-indigo-500">
                    <span>Upload a file</span>
                    <input @drag="upload('birthday-certificate', 'user_birthday_certificate')"
                           @change="upload('birthday-certificate', 'user_birthday_certificate')"
                           required id="birthday-certificate" name="file" type="file"  accept="image/*, .pdf, .doc" class="sr-only" />
                   <span style="color: red;">* </span>:</label>
                  <p class="pl-1">or drag and drop</p>
                </div>
                <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
              </div>
            </div>
            <div id="birthday-certificate-preview" class="h-52 hidden justify-center"
                 style="background-size: cover; background-position: center;
                 background-repeat: no-repeat; background-origin: content-box"></div>
            <input type="hidden" name="user_birthday_certificate_url">
          </div>
        </div>
      </div>
      <div class="border-b border-gray-900/10 pb-12">
        <h2 class="text-base/7 font-semibold text-gray-900">Residency information</h2>
        <div class="sm:col-span-3 mt-10">
            <label for="country" class="block text-sm/6 font-medium text-gray-900">Country of residency <span style="color: red;">* </span>:</label>
            <div class="mt-2 grid grid-cols-1">
              <select required id="region-birth" v-model="countryResidencyCode"  name="user_residency_country_code"
                      class="w-full block min-w-0 mb-6 rounded-md bg-white/5
              sm:text-sm/6 px-4 py-5 text-base peer/email drop-shadow-none shadow-none bg-white text-gray-900 outline
               outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-600 focus:outline focus:outline-2
               focus:-outline-offset-2 focus:ring-green-600 focus:shadow-none focus:drop-shadow-none
               focus:outline-green-600 border-slate-300">
                <option v-for="country in countries" :key="country.iso2" v-bind:value="country.iso2">{{country.name}}</option>
              </select>
            </div>
        </div>
        <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-9" v-show="countryResidencyCode === 'CM' ">
          <div class="sm:col-span-3  sm:col-start-1">
            <label for="region-residency" class="block text-sm/6 font-medium text-gray-900">Region of residency <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select required id="region-birth" v-model="regionResidencyCode"
                      @change="updateDepartmentResidencyList(regionResidencyCode)" name="" class="w-full block min-w-0 mb-6
              rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option value="LT">Littoral</option>
                <option value="OU">West</option>
                <option value="NO">North</option>
                <option value="EN">Far North</option>
                <option value="ES">Centre</option>
                <option value="SU">Sud</option>
                <option value="NW">North-West</option>
                <option value="SW">Sud-West</option>
                <option value="AD">Adamawa</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-3" v-show="countryResidencyCode === 'CM' ">
            <label for="department-birth" class="block text-sm/6 font-medium text-gray-900">Department of residency <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="department-birth" v-model="departmentResidency"  @change="updateMunicipalityList(departmentResidency)"
                      name="" class="w-full block min-w-0
              mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="department in departmentResidencyList" :value="department.name">{{department.name}}</option>
              </select>
            </div>
          </div>
          <div class="sm:col-span-3" v-show="countryResidencyCode === 'CM' ">
            <label for="department-birth" class="block text-sm/6 font-medium text-gray-900">Municipality of residency <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <select id="department-birth" name="user_residency_municipality" v-model="municipalityResidency"
                      class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300">
                <option v-for="municipality in municipalities" :value="municipality.id">{{ municipality.name }}</option>
              </select>
            </div>
          </div>


        </div>
        <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-12">
          <div class="col-span-3">
                      <label for="street-address-residency" class="block text-sm/6 font-medium text-gray-900">Street address</label>
                      <div class="mt-2">
                        <input type="text" name="user_address" id="street-address" autocomplete="off"
                               class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
                         drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                          placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                           focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="1.239 rue Toyota"/>
                      </div>
                    </div>
          <div class="sm:col-span-3">
                      <label for="city-residency" class="block text-sm/6 font-medium text-gray-900">City</label>
                      <div class="mt-2">
                        <input type="text" name="user_residency_city" id="city-residency" autocomplete="off"
                               class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
                         drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                          placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                           focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="Douala"/>
                      </div>
                    </div>
          <div class="sm:col-span-3">
                      <label for="state-residency" class="block text-sm/6 font-medium text-gray-900">State / Province</label>
                      <div class="mt-2">
                        <input type="text" name="user_residency_state" id="state-residency" autocomplete="off"
                               class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
                         drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                          placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                           focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="Littoral"/>
                      </div>
                    </div>
          <div class="sm:col-span-3">
                      <label for="postal-code" class="block text-sm/6 font-medium text-gray-900">ZIP / Postal code</label>
                      <div class="mt-2">
                        <input type="text" name="user_postal_code" id="postal-code" autocomplete="off" class="w-full block
                        min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
                         drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                          placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                           focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" placeholder="4221"/>
                      </div>
                    </div>
        </div>
      </div>

      <div class="border-b border-gray-900/10 pb-12">
        <h2 class="text-base/7 font-semibold text-gray-900">Delivery Information</h2>
        <p class="mt-1 text-sm/6 text-gray-600">Use a permanent address where you can easily get delivered</p>

        <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">

          <div class="col-span-full">
            <label for="delivery-address" class="block text-sm/6 font-medium text-gray-900">Full address <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <input required type="text" name="destination_address" placeholder="1 Meta Way, Menlo Park, CA 94025, USA."
                     id="delivery-address" autocomplete="off"
                     class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" />
            </div>
          </div>

          <div class="sm:col-span-3">
            <label for="city" class="block text-sm/6 font-medium text-gray-900">Place called <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <input required type="text" name="destination_location" id="city" autocomplete="off"
                     class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300" />
            </div>
          </div>

          <div class="sm:col-span-3">
            <label for="region" class="block text-sm/6 font-medium text-gray-900">Close friend phone <span style="color: red;">* </span>:</label>
            <div class="mt-2">
              <div class="absolute items-center ps-3.5 pointer-events-none">
                <svg class="w-5 h-5 mt-5 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 19 18">
                  <path d="M18 13.446a3.02 3.02 0 0 0-.946-1.985l-1.4-1.4a3.054 3.054 0 0 0-4.218 0l-.7.7a.983.983 0 0 1-1.39 0l-2.1-2.1a.983.983 0 0 1 0-1.389l.7-.7a2.98 2.98 0 0 0 0-4.217l-1.4-1.4a2.824 2.824 0 0 0-4.218 0c-3.619 3.619-3 8.229 1.752 12.979C6.785 16.639 9.45 18 11.912 18a7.175 7.175 0 0 0 5.139-2.325A2.9 2.9 0 0 0 18 13.446Z"/>
                </svg>
              </div>
              <input required type="text" name="user_close_friend_number" id="close-friend-phone" autocomplete="off"
                     class="w-full block min-w-0 mb-6 rounded-md bg-white/5 sm:text-sm/6 px-4 py-5 text-base peer/email
               drop-shadow-none shadow-none bg-white text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300
                placeholder:text-gray-600 focus:outline focus:outline-2 focus:-outline-offset-2 focus:ring-green-600
                 focus:shadow-none focus:drop-shadow-none focus:outline-green-600 border-slate-300 ps-12 p-1.5" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mt-6 mb-10 flex items-center justify-end gap-x-6">
<!--      <button type="button" class="text-sm/6 font-semibold text-gray-600 shadow-xs rounded-md bg-gray-300 px-3.5 py-2.5-->
<!--      lg:w-44 sm:w-40 w-full h-14 hover:bg-gray-200 focus-visible:outline-2-->
<!--         focus-visible:outline-offset-2 focus-visible:outline-gray-200">Cancel</button>-->
      <button id="save" type="submit" class="shadow-xs rounded-md bg-green-500 px-3.5 py-2.5 float-right lg:w-44 sm:w-40 w-full h-14
         text-sm font-semibold text-white shadow-xs hover:bg-green-400 focus-visible:outline-2
         focus-visible:outline-offset-2 focus-visible:outline-green-500">
        <svg v-if="submitted" class="w-5 h-5 text-white animate-spin" fill="none"
             viewBox="0 0 24 24"
             xmlns="http://www.w3.org/2000/svg" style="float: left">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                fill="currentColor"></path>
        </svg>
        <span style="margin-left:-10px">Save</span>
      </button>
    </div>
    <input type="hidden" name="user_lang" v-model="browserLanguage" readonly>
  </form>

</template>

<style scoped>

</style>