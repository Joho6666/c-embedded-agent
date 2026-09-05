#include <stdio.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void worker_task(void *pvParameters)
{
    ESP_LOGI("worker", "Worker task active");
    ESP_LOGI("cea", "CEA:ESP32:PASS");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    xTaskCreate(worker_task, "worker_task", 2048, NULL, 5, NULL);
}
