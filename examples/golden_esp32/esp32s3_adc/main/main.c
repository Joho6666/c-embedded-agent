#include <stdio.h>
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define ADC_EXAMPLE_CHAN ADC_CHANNEL_0

void app_main(void)
{
    adc_oneshot_unit_handle_t adc1_handle;
    adc_oneshot_unit_init_cfg_t init_config1 = {
        .unit_id = ADC_UNIT_1,
    };
    adc_oneshot_new_unit(&init_config1, &adc1_handle);

    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    adc_oneshot_config_channel(adc1_handle, ADC_EXAMPLE_CHAN, &config);

    ESP_LOGI("cea", "CEA:ESP32:PASS");

    while (1) {
        int val = 0;
        adc_oneshot_read(adc1_handle, ADC_EXAMPLE_CHAN, &val);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
