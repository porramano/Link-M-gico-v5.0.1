import os
import json
import openai
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIConversationEngine:
    """Motor de IA conversacional avançado para vendas"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_API_BASE')
        )
        self.conversation_history = {}
        self.sales_prompts = self._load_sales_prompts()
        
    def _load_sales_prompts(self) -> Dict[str, str]:
        """Carrega prompts especializados para vendas"""
        return {
            "system_base": """Você é um vendedor profissional altamente qualificado, especialista em conversão e persuasão. 
            Suas características principais:
            - Extremamente empático e emocional nas respostas
            - Nunca dá respostas engessadas ou robóticas
            - Sempre adapta a conversa ao contexto do usuário
            - Usa técnicas avançadas de copywriting e persuasão
            - Identifica objeções e as contorna de forma natural
            - Cria senso de urgência quando apropriado
            - Mantém um tom humano, caloroso e convincente
            - Nunca quebra o personagem ou admite ser um bot
            - Foca sempre em benefícios, não apenas características
            - Usa storytelling para conectar emocionalmente""",
            
            "greeting": """Responda como um vendedor experiente que acabou de conhecer um cliente em potencial. 
            Seja caloroso, interessado genuinamente na pessoa e crie uma conexão emocional imediata.""",
            
            "objection_handling": """O cliente apresentou uma objeção. Como vendedor expert:
            1. Reconheça a preocupação com empatia
            2. Reframe a objeção como uma oportunidade
            3. Apresente uma solução convincente
            4. Use prova social ou casos de sucesso
            5. Redirecione para o valor e benefícios""",
            
            "closing": """É hora de fechar a venda. Use técnicas de fechamento como:
            - Assumptive close (assumir que vai comprar)
            - Alternative choice (dar opções de compra)
            - Urgency close (criar senso de urgência)
            - Benefit summary (resumir benefícios principais)
            Seja direto mas não agressivo.""",
            
            "follow_up": """Continue a conversa de forma natural, mantendo o interesse e direcionando para a ação desejada."""
        }
    
    def analyze_user_intent(self, message: str, context: Dict) -> Dict[str, any]:
        """Analisa a intenção do usuário e contexto emocional"""
        try:
            analysis_prompt = f"""
            Analise esta mensagem do usuário e retorne um JSON com:
            - intent: (greeting, question, objection, interest, ready_to_buy, price_inquiry, comparison, other)
            - sentiment: (positive, negative, neutral)
            - urgency_level: (low, medium, high)
            - buying_stage: (awareness, consideration, decision)
            - emotional_state: (excited, skeptical, confused, frustrated, curious)
            - key_concerns: [lista de preocupações identificadas]
            
            Mensagem: "{message}"
            Contexto da conversa: {json.dumps(context.get('previous_messages', [])[-3:], ensure_ascii=False)}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise de intenção e psicologia do consumidor. Retorne apenas JSON válido."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Erro na análise de intenção: {e}")
            return {
                "intent": "other",
                "sentiment": "neutral",
                "urgency_level": "medium",
                "buying_stage": "consideration",
                "emotional_state": "curious",
                "key_concerns": []
            }
    
    def generate_persuasive_response(self, message: str, context: Dict, web_data: Optional[Dict] = None) -> str:
        """Gera resposta persuasiva baseada no contexto e dados da web"""
        try:
            # Analisa intenção do usuário
            intent_analysis = self.analyze_user_intent(message, context)
            
            # Seleciona prompt base baseado na intenção
            prompt_key = self._select_prompt_strategy(intent_analysis)
            base_prompt = self.sales_prompts.get(prompt_key, self.sales_prompts["follow_up"])
            
            # Constrói contexto completo
            full_context = self._build_conversation_context(context, web_data, intent_analysis)
            
            # Gera resposta personalizada
            system_message = f"{self.sales_prompts['system_base']}\n\n{base_prompt}\n\nContexto adicional: {full_context}"
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Mensagem do cliente: {message}"}
                ],
                temperature=0.8,  # Mais criativo para respostas naturais
                max_tokens=800,
                presence_penalty=0.6,  # Evita repetições
                frequency_penalty=0.4
            )
            
            generated_response = response.choices[0].message.content
            
            # Pós-processa a resposta para adicionar elementos persuasivos
            final_response = self._enhance_response_with_persuasion(generated_response, intent_analysis, web_data)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {e}")
            return self._get_fallback_response(intent_analysis.get("intent", "other"))
    
    def _select_prompt_strategy(self, intent_analysis: Dict) -> str:
        """Seleciona estratégia de prompt baseada na análise de intenção"""
        intent = intent_analysis.get("intent", "other")
        buying_stage = intent_analysis.get("buying_stage", "consideration")
        
        if intent == "greeting":
            return "greeting"
        elif intent == "objection":
            return "objection_handling"
        elif intent == "ready_to_buy" or buying_stage == "decision":
            return "closing"
        else:
            return "follow_up"
    
    def _build_conversation_context(self, context: Dict, web_data: Optional[Dict], intent_analysis: Dict) -> str:
        """Constrói contexto completo da conversa"""
        context_parts = []
        
        # Histórico da conversa
        if context.get('previous_messages'):
            recent_messages = context['previous_messages'][-5:]  # Últimas 5 mensagens
            context_parts.append(f"Histórico recente: {json.dumps(recent_messages, ensure_ascii=False)}")
        
        # Dados da web se disponíveis
        if web_data:
            context_parts.append(f"Informações do produto/serviço: {json.dumps(web_data, ensure_ascii=False)}")
        
        # Análise de intenção
        context_parts.append(f"Análise do cliente: {json.dumps(intent_analysis, ensure_ascii=False)}")
        
        # Perfil do cliente (se disponível)
        if context.get('user_profile'):
            context_parts.append(f"Perfil do cliente: {json.dumps(context['user_profile'], ensure_ascii=False)}")
        
        return "\n".join(context_parts)
    
    def _enhance_response_with_persuasion(self, response: str, intent_analysis: Dict, web_data: Optional[Dict]) -> str:
        """Adiciona elementos persuasivos à resposta"""
        enhanced_response = response
        
        # Adiciona CTA baseado no estágio de compra
        buying_stage = intent_analysis.get("buying_stage", "consideration")
        if buying_stage == "decision" and not self._has_cta(response):
            enhanced_response += self._generate_cta(intent_analysis)
        
        # Adiciona prova social se apropriado
        if intent_analysis.get("emotional_state") == "skeptical":
            enhanced_response = self._add_social_proof(enhanced_response)
        
        # Adiciona urgência se necessário
        urgency = intent_analysis.get("urgency_level", "medium")
        if urgency == "low" and buying_stage in ["consideration", "decision"]:
            enhanced_response = self._add_urgency_element(enhanced_response)
        
        return enhanced_response
    
    def _has_cta(self, response: str) -> bool:
        """Verifica se a resposta já tem uma chamada para ação"""
        cta_indicators = [
            "clique", "acesse", "compre", "adquira", "garanta", "aproveite",
            "entre em contato", "fale conosco", "solicite", "peça"
        ]
        return any(indicator in response.lower() for indicator in cta_indicators)
    
    def _generate_cta(self, intent_analysis: Dict) -> str:
        """Gera chamada para ação apropriada"""
        ctas = [
            "\n\n🎯 Que tal darmos o próximo passo? Posso te ajudar com mais detalhes agora mesmo!",
            "\n\n✨ Vamos transformar esse interesse em realidade? Estou aqui para te guiar!",
            "\n\n🚀 Pronto para começar? Vou te mostrar exatamente como proceder!"
        ]
        return ctas[hash(str(intent_analysis)) % len(ctas)]
    
    def _add_social_proof(self, response: str) -> str:
        """Adiciona prova social à resposta"""
        social_proofs = [
            "\n\nAliás, mais de 95% dos nossos clientes ficam completamente satisfeitos com os resultados!",
            "\n\nVocê sabia que já ajudamos milhares de pessoas como você a alcançar seus objetivos?",
            "\n\nNossos clientes sempre comentam como essa foi uma das melhores decisões que tomaram!"
        ]
        return response + social_proofs[len(response) % len(social_proofs)]
    
    def _add_urgency_element(self, response: str) -> str:
        """Adiciona elemento de urgência à resposta"""
        urgency_elements = [
            "\n\n⏰ Aproveite que estou online agora para te atender com toda atenção!",
            "\n\n🔥 Esse é o momento perfeito para agir - as condições estão ideais!",
            "\n\n💎 Oportunidades como essa não aparecem todos os dias!"
        ]
        return response + urgency_elements[len(response) % len(urgency_elements)]
    
    def _get_fallback_response(self, intent: str) -> str:
        """Retorna resposta de fallback em caso de erro"""
        fallbacks = {
            "greeting": "Olá! É um prazer falar com você! Como posso te ajudar hoje? 😊",
            "objection": "Entendo sua preocupação, e é completamente normal ter essas dúvidas. Deixe-me esclarecer isso para você...",
            "question": "Excelente pergunta! Vou te dar uma resposta completa e detalhada...",
            "other": "Que interessante! Conte-me mais sobre isso para que eu possa te ajudar da melhor forma possível!"
        }
        return fallbacks.get(intent, fallbacks["other"])
    
    def update_conversation_history(self, session_id: str, user_message: str, bot_response: str, context: Dict):
        """Atualiza histórico da conversa"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "context": context
        })
        
        # Mantém apenas as últimas 20 interações por sessão
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-20:]
    
    def get_conversation_context(self, session_id: str) -> Dict:
        """Recupera contexto da conversa"""
        history = self.conversation_history.get(session_id, [])
        return {
            "previous_messages": [
                {"user": msg["user_message"], "bot": msg["bot_response"]} 
                for msg in history[-10:]  # Últimas 10 interações
            ],
            "session_start": history[0]["timestamp"] if history else datetime.now().isoformat(),
            "total_interactions": len(history)
        }

