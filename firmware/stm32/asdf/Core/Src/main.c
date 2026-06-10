/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 STMicroelectronics.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "can.h"
#include "i2c.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include "bh1750.h"
#include "mk_dht11.h"
#include "i2c.h"
#include "i2c_lcd.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
// 센서 및 모듈 제어용 구조체 선언
I2C_LCD_HandleTypeDef hlcd;
dht11_t dht;

// 센서 데이터 변수
float temp = 0.0f;
float humidity = 0.0f;
float lux = 0.0f;
int current_speed = 0;

// JSON 통신 및 디버깅용 버퍼
char tx_buffer[256];
char debug_buffer[256];
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
// 1. 차량 고유번호 지정
const char* VEHICLE_ID = "5632";

// 2. 좌표 (위도, 경도)
// (서울좌표 : 37.5665f, 126.9780f)
// (부산좌표 : 35.1796f, 129.0756f)
// (해남좌표 : 34.5567f, 126.5751f)
const float LAT = 34.5567f;
const float LON = 126.5751f;
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_ADC1_Init();
  MX_CAN1_Init();
  MX_I2C1_Init();
  MX_USART2_UART_Init();
  MX_USART6_UART_Init();
  MX_TIM1_Init();
  MX_I2C2_Init();
  /* USER CODE BEGIN 2 */

  	// 1. BH1750 조도 센서 초기화 및 측정 모드 실행
  	BH1750_Init(&hi2c1);
  	// 센서를 깨우고 '연속 고해상도 측정 모드'로 설정
  	BH1750_SetMode(CONTINUOUS_HIGH_RES_MODE);

  	HAL_Delay(100);

  	// 2. I2C LCD 초기화
  	hlcd.hi2c = &hi2c2;
  	hlcd.address = 0x4E;
  	lcd_init(&hlcd);
  	lcd_puts(&hlcd, "System On");

  	// 3. DHT11 초기화
  	init_dht11(&dht, &htim1, GPIOB, GPIO_PIN_0);

  	HAL_Delay(1500);
  	// lcd_clear(&hlcd);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
	while (1) {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
		// 1. 온습도(DHT11) 읽기
		readDHT11(&dht);
		temp = (float) dht.temperature;
		humidity = (float) dht.humidty;

		// 2. 조도(BH1750) 읽기
		float temp_lux = 0.0f;
		if (BH1750_ReadLight(&temp_lux) == BH1750_OK) {
		    lux = temp_lux;
		} else {
		    // 통신이 실패하면 값은 -1
		    lux = -1.0f;
		}

		// 3. 가상 속도(ADC 가변 저항) 읽기 (PA0 핀)
		HAL_ADC_Start(&hadc1);
		if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK) {
			uint32_t adc_val = HAL_ADC_GetValue(&hadc1);
			current_speed = (adc_val * 150) / 4095; // 0~150km/h로 매핑
		}

		// 4. LCD 디스플레이 업데이트
		char lcd_buf[1];
		lcd_gotoxy(&hlcd, 0, 0); // 첫째 줄로 이동
		sprintf(lcd_buf, "T:%02dC H:%02d%%", (int) temp, (int) humidity);
		lcd_puts(&hlcd, lcd_buf);

		lcd_gotoxy(&hlcd, 0, 1); // 둘째 줄로 이동
		sprintf(lcd_buf, "L:%04d S:%03d", (int) lux, current_speed);
		lcd_puts(&hlcd, lcd_buf);

		// 5. ESP32로 보낼 JSON 문자열 포장
		sprintf(tx_buffer,
				"\r\n\r\n{\"vid\":\"%s\",\"lat\":%.4f,\"lon\":%.4f,\"temp\":%.1f,\"humidity\":%.1f,\"lux\":%.1f,\"speed\":%d}\r\n",
		        VEHICLE_ID, LAT, LON, temp, humidity, lux, current_speed);

		// 6. ESP32로 전송 (USART6)
		HAL_UART_Transmit(&huart6, (uint8_t*) tx_buffer, strlen(tx_buffer),
				100);

		// 7. PC 모니터 출력 (디버깅용, USART2)
		sprintf(debug_buffer, "[SEND] %s", tx_buffer);
		HAL_UART_Transmit(&huart2, (uint8_t*) debug_buffer,
				strlen(debug_buffer), 100);

		// 8. 1초 대기
		HAL_Delay(1000);
	}
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 8;
  RCC_OscInitStruct.PLL.PLLN = 50;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
	/* User can add his own implementation to report the HAL error return state */
	__disable_irq();
	while (1) {
	}
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
