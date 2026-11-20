package com.example.controller;

import com.example.exception.GlobalExceptionHandler;
import com.example.service.ExampleService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Controller 片测：验证契约字段名而不是实现细节。
 * code / msg / data.xxx 的断言必须与契约样例逐字一致：前端按这些键取值，
 * 写成 message 或少一层 data 都会让联调翻车，这几行断言就是契约在代码侧的镜像。
 * @Import GlobalExceptionHandler 让错误路径也被真实覆盖。
 */
@WebMvcTest(controllers = ExampleController.class)
@Import(GlobalExceptionHandler.class)
@DisplayName("示例接口契约一致性测试")
class ExampleControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ExampleService service;

    @Test
    @DisplayName("2xx：Result 包裹 + 字段名与契约一致")
    void createReturnsResultEnvelope() throws Exception {
        when(service.create(any())).thenReturn("1859234567890123456");

        mockMvc.perform(post("/api/v1/examples")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"demo\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").isString())
                .andExpect(jsonPath("$.data.id").value("1859234567890123456"));
    }

    @Test
    @DisplayName("参数校验失败：返回契约登记的 40001，不是 Spring 默认 400 页面")
    void blankNameReturnsRegisteredErrorCode() throws Exception {
        mockMvc.perform(post("/api/v1/examples")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(40001));
    }
}
