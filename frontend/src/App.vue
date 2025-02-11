<template>
  <div class="chat-container">
    <div class="header">
      <h1>AI 聊天助手</h1>
      <el-button type="primary" @click="startNewChat" :disabled="loading">
        <i class="el-icon-plus"></i> 开始新对话
      </el-button>
    </div>
    <div class="chat-messages" ref="messageContainer">
      <div v-for="(message, index) in currentChat.messages" :key="index"
        :class="['message', message.role === 'user' ? 'user-message' : 'bot-message']">
        <div class="avatar">
          <img v-if="message.role === 'bot'" :src="botAvatar" alt="Bot">
          <div v-else class="user-avatar">用户</div>
        </div>
        <div class="message-content">
          <template v-if="message.role === 'bot'">
            <div class="bot-response">
              <div v-if="message.reasoning" class="reasoning-container">
                <div class="reasoning-header">
                  <span class="icon">🤔</span>
                  <span>思考过程</span>
                  <span class="time" v-if="!message.isThinking">用时 {{ message.thinkingTime || 0 }}秒</span>
                </div>
                <div class="reasoning" v-html="renderMarkdown(message.reasoning)"></div>
              </div>
              <div v-if="message.showAnswer" class="answer-container">
                <div class="answer-header">
                  <span class="icon">💡</span>
                  <span>完整回复</span>
                </div>
                <div class="final-answer" v-html="renderMarkdown(message.content)"></div>
              </div>
              <div v-if="message.isThinking" class="thinking">
                <span class="dot-1">.</span>
                <span class="dot-2">.</span>
                <span class="dot-3">.</span>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="user-content" v-html="renderMarkdown(message.content)"></div>
          </template>
        </div>
      </div>
    </div>
    <div class="input-container">
      <el-input v-model="userInput" placeholder="请输入消息..." @keyup.enter="sendMessage" :disabled="loading">
        <template #append>
          <el-button @click="sendMessage" :loading="loading">发送</el-button>
        </template>
      </el-input>
    </div>
  </div>
</template>

<script>
import { ref, reactive, nextTick } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { OpenAI } from 'openai'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked
marked.setOptions({
  breaks: true,  // 支持 GitHub 风格的换行
  gfm: true      // 支持 GitHub 风格的 Markdown
})

const client = new OpenAI({
  apiKey: process.env.VUE_APP_DASHSCOPE_API_KEY,
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  dangerouslyAllowBrowser: true
})

// 导入狮子头像
import botAvatar from './assets/cover.jpg'

export default {
  name: 'App',
  setup() {
    const currentChat = reactive({
      id: Date.now(),
      messages: [],
      apiMessages: []
    })
    const userInput = ref('')
    const loading = ref(false)
    const messageContainer = ref(null)
    let startTime = 0

    const renderMarkdown = (text) => {
      if (!text) return ''
      // 使用 DOMPurify 清理 HTML，防止 XSS 攻击
      return DOMPurify.sanitize(marked(text))
    }

    const scrollToBottom = () => {
      setTimeout(() => {
        if (messageContainer.value) {
          messageContainer.value.scrollTop = messageContainer.value.scrollHeight
        }
      }, 100)
    }

    const startNewChat = () => {
      currentChat.id = Date.now()
      currentChat.messages = []
      currentChat.apiMessages = []
      userInput.value = ''
    }

    const saveRecord = async (userMessage, botMessage) => {
      try {
        const timestamp = new Date().toLocaleString('zh-CN', {
          timeZone: 'Asia/Shanghai',
          hour12: false
        })

        const record = {
          timestamp,
          chatId: currentChat.id,
          userMessage,
          botReasoning: botMessage.reasoning,
          botResponse: botMessage.content,
          thinkingTime: botMessage.thinkingTime
        }

        await axios.post('http://localhost:8000/save-record', record)
      } catch (error) {
        console.error('保存对话记录失败:', error)
      }
    }

    const sendMessage = async () => {
      if (!userInput.value.trim() || loading.value) return

      const userMessage = userInput.value
      const userMessageObj = { role: 'user', content: userMessage }
      currentChat.messages.push(userMessageObj)
      currentChat.apiMessages.push(userMessageObj)
      userInput.value = ''
      loading.value = true
      scrollToBottom()

      try {
        const botMessage = reactive({
          role: 'bot',
          content: '',
          reasoning: '',
          isThinking: true,
          thinkingTime: 0,
          showAnswer: false
        })
        currentChat.messages.push(botMessage)
        startTime = Date.now()

        const stream = await client.chat.completions.create({
          model: 'deepseek-r1',
          messages: currentChat.apiMessages,
          stream: true
        })

        let isFirstContent = true

        for await (const chunk of stream) {
          if (chunk.choices[0]?.delta?.reasoning_content) {
            const newText = chunk.choices[0].delta.reasoning_content
            botMessage.reasoning += newText
            await nextTick()
          }
          else if (chunk.choices[0]?.delta?.content) {
            if (isFirstContent) {
              isFirstContent = false
              botMessage.thinkingTime = ((Date.now() - startTime) / 1000).toFixed(1)
              botMessage.showAnswer = true
            }
            const newText = chunk.choices[0].delta.content
            botMessage.content += newText
            await nextTick()
          }
          scrollToBottom()
        }

        // 更新API消息历史
        currentChat.apiMessages.push({
          role: 'assistant',
          content: botMessage.content
        })

        // 所有内容接收完毕后，保存记录并关闭思考状态
        botMessage.isThinking = false
        await saveRecord(userMessage, botMessage)
      } catch (error) {
        ElMessage.error('发送消息失败，请重试')
        console.error('发送消息失败:', error)
      } finally {
        loading.value = false
        scrollToBottom()
      }
    }

    return {
      currentChat,
      userInput,
      loading,
      botAvatar,
      messageContainer,
      sendMessage,
      startNewChat,
      renderMarkdown
    }
  }
}
</script>

<style>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 0 20px;
}

.header h1 {
  margin: 0;
  font-size: 1.5em;
  color: #333;
}
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  margin-bottom: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.message {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
}

.avatar {
  width: 40px;
  height: 40px;
  margin-right: 10px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-avatar {
  width: 100%;
  height: 100%;
  background: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.message-content {
  background: white;
  padding: 15px;
  border-radius: 8px;
  max-width: 70%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.bot-response {
  position: relative;
}

.user-message {
  flex-direction: row-reverse;
}

.user-message .avatar {
  margin-right: 0;
  margin-left: 10px;
}

.user-message .message-content {
  background: #409EFF;
  color: white;
}

.input-container {
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
}

.thinking {
  color: #666;
  font-size: 24px;
  line-height: 1;
  display: inline-flex;
  gap: 2px;
  margin-left: 4px;
  vertical-align: bottom;
}

.thinking .dot-1,
.thinking .dot-2,
.thinking .dot-3 {
  animation: bounce 1s infinite;
}

.thinking .dot-2 {
  animation-delay: 0.2s;
}

.thinking .dot-3 {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-6px);
  }
}

.reasoning-container,
.answer-container {
  margin-bottom: 10px;
}

.reasoning-header,
.answer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.9em;
  color: #666;
}

.icon {
  font-size: 1.2em;
}

.time {
  margin-left: auto;
  font-size: 0.85em;
}

.reasoning {
  color: #666;
  font-size: 0.95em;
  white-space: pre-wrap;
  margin-left: 24px;
}

.final-answer {
  color: #000;
  white-space: pre-wrap;
  margin-left: 24px;
}

.user-content {
  white-space: pre-wrap;
}

/* Markdown 样式 */
.message-content :deep(p) {
  margin: 0.5em 0;
}

.message-content :deep(pre) {
  background: #f8f8f8;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

.message-content :deep(code) {
  background: #f8f8f8;
  padding: 2px 4px;
  border-radius: 2px;
  font-family: monospace;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 20px;
}

.message-content :deep(blockquote) {
  margin: 0.5em 0;
  padding-left: 1em;
  border-left: 4px solid #ddd;
  color: #666;
}

.user-message .message-content :deep(pre),
.user-message .message-content :deep(code) {
  background: rgba(0, 0, 0, 0.1);
}

.user-message .message-content :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.4);
}
</style>