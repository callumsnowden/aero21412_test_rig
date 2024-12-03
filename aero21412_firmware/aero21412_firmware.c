#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/uart.h"
#include "hardware/pio.h"
#include "hardware/pwm.h"

// HX711 library include
#include "extern/hx711-pico-c/include/common.h"

// I2C defines
// I2C0 on GPIO8 (SDA) and GPIO9 (SCL) running at 400KHz.
#define I2C_PORT i2c0
#define I2C_SDA 8
#define I2C_SCL 9
#define ADS1100_ADDR 0x4B

// UART defines
// By default the stdout UART is `uart0`, so we will use the second one
#define UART_ID uart0
#define BAUD_RATE 115200

// Use pins 0 and 1 for UART0
// Pins can be changed, see the GPIO function select table in the datasheet for information on GPIO assignments
#define UART_TX_PIN 0
#define UART_RX_PIN 1

// GPIO defines
#define LED_GPIO_PIN 16
#define BUTTON_GPIO_PIN 2
#define TACHO_IN_PIN 3
#define TACHO_PWM_PIN 4

// Variables
bool LED_STATE = false;
uint8_t i2c_rxdata[3];
int16_t adc_raw = 0;
uint8_t adc_conf = 0x08;
float adc_voltage = 0.0;

void tacho_pwm_wrap() {
    // TODO: write pwm wrap handler
}

int main()
{
    stdio_init_all();

    // I2C Initialisation. Using it at 400Khz.
    i2c_init(I2C_PORT, 100*1000);
    
    gpio_set_function(I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA);
    gpio_pull_up(I2C_SCL);

    // Set up UART
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    // Set up all GPIO pins
    gpio_init(LED_GPIO_PIN);
    gpio_set_dir(LED_GPIO_PIN, GPIO_OUT);
    gpio_put(LED_GPIO_PIN, LED_STATE);

    gpio_init(BUTTON_GPIO_PIN);
    gpio_set_dir(BUTTON_GPIO_PIN, GPIO_IN);

    gpio_init(TACHO_IN_PIN);
    gpio_set_dir(TACHO_IN_PIN, GPIO_IN);

    gpio_set_function(TACHO_PWM_PIN, GPIO_FUNC_PWM);
    uint tacho_pwm_slice_num = pwm_gpio_to_slice_num(TACHO_PWM_PIN);
    pwm_config tacho_pwm_config = pwm_get_default_config();
    pwm_config_set_clkdiv(&tacho_pwm_config, 4.f);
    pwm_init(tacho_pwm_slice_num, &tacho_pwm_config, true);
    
    // Use some the various UART functions to send out data
    // In a default system, printf will also output via the default UART
    // Send out a string, with CR/LF conversions
    uart_puts(UART_ID, " Hello, UART!\n");
    
    // HX711 configuration
    hx711_config_t hxcfg;
    hx711_get_default_config(&hxcfg);
    hxcfg.clock_pin = 6;
    hxcfg.data_pin = 7;
    hx711_t hx;
    hx711_init(&hx, &hxcfg);
    hx711_power_up(&hx, hx711_gain_128);

    // set up 10 conversions per second rate
    hx711_wait_settle(hx711_rate_10);

    printf("HX711 configured\n");
    
    // For more examples of UART use see https://github.com/raspberrypi/pico-examples/tree/master/uart


    uint8_t ret = 0;

    // Set up ADC for 16sps, 1x gain (PGA not used)
    ret = i2c_write_blocking(I2C_PORT, ADS1100_ADDR, adc_conf, 1, false);

    while (true) {
        ret = i2c_read_blocking(I2C_PORT, ADS1100_ADDR, i2c_rxdata, 3, false);
        adc_raw = (i2c_rxdata[0] << 8) | i2c_rxdata[1];
        adc_voltage = ((5.0/16384) * adc_raw);
        printf("ADC mV %f \n", adc_voltage);
        printf("Scale value: %li\n", hx711_get_value(&hx));
        gpio_put(LED_GPIO_PIN, !LED_STATE);
    }
}
