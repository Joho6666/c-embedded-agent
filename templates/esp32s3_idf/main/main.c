#include <stdio.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define CEA_OUTPUT_GPIO GPIO_NUM_4

void app_main(void)
{
    gpio_reset_pin(CEA_OUTPUT_GPIO);
    gpio_set_direction(CEA_OUTPUT_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(CEA_OUTPUT_GPIO, 1);
    ESP_LOGI("cea", "CEA:ESP32:PASS");

    while (1) {
        gpio_set_level(CEA_OUTPUT_GPIO, !gpio_get_level(CEA_OUTPUT_GPIO));
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
