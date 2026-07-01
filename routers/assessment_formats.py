"""
Assessment format definitions — maps assessment keys to section/exercise configs.
Format types: voice_test | voice_scenario | text_writing | coding_test | mcq
"""
from typing import List, Dict, Any

ASSESSMENT_FORMAT_MAP: Dict[str, str] = {
    'bpo_versant_pro': 'voice_test',
    'bpo_accent_neutral': 'voice_test',
    'av_cabin_comm': 'voice_test',
    'edu_teaching_demo': 'voice_test',
    'bpo_cust_handling': 'voice_scenario',
    'bpo_objection_handling': 'voice_scenario',
    'bpo_call_quality': 'voice_scenario',
    'sales_video_pitch': 'voice_scenario',
    'sales_objection_sim': 'voice_scenario',
    'sales_lead_conv': 'voice_scenario',
    'sales_empathy': 'voice_scenario',
    'hc_communication': 'voice_scenario',
    'hc_case_handling': 'voice_scenario',
    'retail_video_test': 'voice_scenario',
    'retail_complaint': 'voice_scenario',
    'av_passenger': 'voice_scenario',
    'edu_delivery': 'voice_scenario',
    'bpo_chat_email_etiquette': 'text_writing',
    'sales_creativity': 'text_writing',
    'con_project_coord': 'text_writing',
    'con_blueprint': 'text_writing',
    'it_adv_coding': 'coding_test',
    'it_algorithmic_thinking': 'coding_test',
    'it_debugging': 'coding_test',
    'it_sql_pro': 'coding_test',
    'it_react_skills': 'coding_test',
    'it_js_pro': 'coding_test',
    'it_system_design_lite': 'coding_test',
    'it_system_design_pro': 'coding_test',
    'tel_troubleshoot': 'coding_test',
    # Free / general plan assessments
    'gen_video_intro':      'voice_scenario',
    'gen_coding_basic':     'coding_test',
    'gen_typing':           'text_writing',
    'gen_aptitude':         'mcq',
    'gen_psychometric':     'mcq',
    'gen_attention_detail': 'mcq',
    'gen_english_prof':     'mcq',
    'gen_resume_quiz':      'text_writing',
    'gen_interview_prep':   'mcq',
    # everything else defaults to 'mcq'
}

FORMAT_DESCRIPTIONS: Dict[str, str] = {
    'voice_test': 'Structured voice test with vocabulary, reading, sentence repetition, verbal Q&A, and free speaking sections.',
    'voice_scenario': 'Voice-based scenario test. Read real-world situations and respond verbally as you would on the job.',
    'text_writing': 'Written communication test. Compose professional emails, chat responses, or written analysis.',
    'coding_test': 'Technical coding test with real programming problems to solve in a code editor.',
    'mcq': 'Multiple-choice knowledge test. Select the best answer for each question.',
}

VOICE_TEST_FORMATS: Dict[str, List[Dict]] = {
    'bpo_versant_pro': [
        {
            'id': 's_vocab', 'title': 'Part 1 — Word Reading',
            'instruction': 'Say each word clearly and at a natural pace. This warms up your pronunciation.',
            'exercise_type': 'vocabulary', 'duration_per_item': 8,
            'items': [
                {'id': 'w1', 'content': 'articulate'}, {'id': 'w2', 'content': 'facilitate'},
                {'id': 'w3', 'content': 'comprehend'}, {'id': 'w4', 'content': 'enumerate'},
                {'id': 'w5', 'content': 'demonstrate'}, {'id': 'w6', 'content': 'professional'},
                {'id': 'w7', 'content': 'efficiently'}, {'id': 'w8', 'content': 'resolution'},
            ]
        },
        {
            'id': 's_read', 'title': 'Part 2 — Reading Aloud',
            'instruction': 'Read each passage aloud at a clear, steady pace. You will be recorded.',
            'exercise_type': 'read_aloud', 'duration_per_item': 60,
            'items': [
                {'id': 'p1', 'content': 'Effective communication in a customer service environment requires clarity, empathy, and patience. When handling a customer complaint, it is essential to listen actively and acknowledge their concern before offering a solution. A professional tone, combined with clear articulation, helps build trust and ensures that the customer feels heard and valued throughout the interaction.'},
                {'id': 'p2', 'content': 'The success of any business depends largely on the quality of its customer relationships. Service representatives are often the first point of contact, making their communication skills critical. Whether through telephone, email, or chat, every interaction is an opportunity to reinforce the company\'s commitment to customer satisfaction and excellence.'}
            ]
        },
        {
            'id': 's_repeat', 'title': 'Part 3 — Sentence Repetition',
            'instruction': 'Press Play to hear each sentence, then repeat it exactly as spoken. Focus on accuracy and clarity.',
            'exercise_type': 'repeat_sentence', 'duration_per_item': 25,
            'items': [
                {'id': 'r1', 'content': 'The customer requested an immediate refund for the damaged product.'},
                {'id': 'r2', 'content': 'Please hold while I transfer your call to the technical support team.'},
                {'id': 'r3', 'content': 'Your account has been updated with the new billing information successfully.'},
                {'id': 'r4', 'content': 'I understand your frustration and I will do my best to resolve this issue.'},
                {'id': 'r5', 'content': 'The service outage affected approximately two thousand customers in the region.'},
                {'id': 'r6', 'content': 'Could you please verify your identity by providing your account number?'}
            ]
        },
        {
            'id': 's_qa', 'title': 'Part 4 — Verbal Questions',
            'instruction': 'Answer each question verbally in complete sentences. You have 45 seconds per question.',
            'exercise_type': 'qa_verbal', 'duration_per_item': 45,
            'items': '__OLLAMA__'
        },
        {
            'id': 's_topic', 'title': 'Part 5 — Topic Speaking',
            'instruction': 'Choose one topic and speak about it for 60 seconds. Take a moment to organise your thoughts before you begin.',
            'exercise_type': 'topic_speaking', 'duration_per_item': 60,
            'items': [
                {'id': 't1', 'content': 'Customer Service Best Practices'},
                {'id': 't2', 'content': 'A Time You Resolved a Difficult Customer Situation'},
                {'id': 't3', 'content': 'The Importance of Active Listening in Customer Support'},
                {'id': 't4', 'content': 'How Technology is Changing the Customer Experience'}
            ]
        }
    ],
    'bpo_accent_neutral': [
        {
            'id': 's_pairs', 'title': 'Part 1 — Sound Pairs',
            'instruction': 'Say each word pair aloud. Focus on the clear difference in sound between the two words.',
            'exercise_type': 'vocabulary', 'duration_per_item': 10,
            'items': [
                {'id': 'p1', 'content': 'ship  /  sheep'}, {'id': 'p2', 'content': 'bit  /  beat'},
                {'id': 'p3', 'content': 'pen  /  pan'}, {'id': 'p4', 'content': 'walk  /  work'},
                {'id': 'p5', 'content': 'light  /  right'}, {'id': 'p6', 'content': 'thin  /  tin'},
                {'id': 'p7', 'content': 'pool  /  pull'}, {'id': 'p8', 'content': 'cat  /  cut'}
            ]
        },
        {
            'id': 's_stress', 'title': 'Part 2 — Word Stress',
            'instruction': 'Read each word with the correct stress. The stressed syllable is shown in CAPITALS.',
            'exercise_type': 'vocabulary', 'duration_per_item': 8,
            'items': [
                {'id': 'w1', 'content': 'pro · FES · sion · al'}, {'id': 'w2', 'content': 'COM · mu · ni · cate'},
                {'id': 'w3', 'content': 'ar · TIC · u · late'}, {'id': 'w4', 'content': 'e · NUN · ci · ate'},
                {'id': 'w5', 'content': 'SIM · i · lar · ly'}, {'id': 'w6', 'content': 'PRO · nounce'},
                {'id': 'w7', 'content': 'VOC · ab · u · la · ry'}
            ]
        },
        {
            'id': 's_sentences', 'title': 'Part 3 — Sentence Reading',
            'instruction': 'Read each sentence aloud with natural rhythm and stress.',
            'exercise_type': 'read_aloud', 'duration_per_item': 30,
            'items': [
                {'id': 's1', 'content': 'I would like to speak to the manager about my bill.'},
                {'id': 's2', 'content': 'Thank you for calling. How can I help you today?'},
                {'id': 's3', 'content': 'The delivery was scheduled for Tuesday but has been delayed.'},
                {'id': 's4', 'content': 'Please allow me to explain the terms of your agreement.'},
                {'id': 's5', 'content': 'We appreciate your patience while we process your request.'}
            ]
        },
        {
            'id': 's_passage', 'title': 'Part 4 — Passage Reading',
            'instruction': 'Read this passage aloud at a clear, neutral pace. Focus on consistent pronunciation throughout.',
            'exercise_type': 'read_aloud', 'duration_per_item': 75,
            'items': [
                {'id': 'r1', 'content': 'A neutral accent makes your speech easier to understand across different regions and cultures. When you speak clearly and at a measured pace, your listener can focus on what you are saying rather than how you are saying it. This is especially important in customer-facing roles where clarity and confidence build trust. Practice by recording yourself and listening for sounds that may be unclear or heavily accented.'}
            ]
        },
        {
            'id': 's_speaking', 'title': 'Part 5 — Free Speaking',
            'instruction': 'Choose a topic and speak about it for 45 seconds. Focus on clarity, pace, and neutral pronunciation.',
            'exercise_type': 'topic_speaking', 'duration_per_item': 45,
            'items': [
                {'id': 't1', 'content': 'Describe your morning routine'},
                {'id': 't2', 'content': 'Talk about a movie or book you enjoyed recently'},
                {'id': 't3', 'content': 'Explain how to prepare your favourite dish'},
                {'id': 't4', 'content': 'Describe the city or town you live in'}
            ]
        }
    ],
    'av_cabin_comm': [
        {
            'id': 's_vocab', 'title': 'Part 1 — Aviation Vocabulary',
            'instruction': 'Read each aviation term clearly and professionally.',
            'exercise_type': 'vocabulary', 'duration_per_item': 8,
            'items': [
                {'id': 'w1', 'content': 'evacuation'}, {'id': 'w2', 'content': 'turbulence'},
                {'id': 'w3', 'content': 'depressurization'}, {'id': 'w4', 'content': 'disembarkation'},
                {'id': 'w5', 'content': 'seatbelt'}, {'id': 'w6', 'content': 'announcement'},
                {'id': 'w7', 'content': 'altitude'}, {'id': 'w8', 'content': 'boarding'}
            ]
        },
        {
            'id': 's_safety', 'title': 'Part 2 — Safety Announcement',
            'instruction': 'Read the following cabin safety announcement aloud clearly and professionally.',
            'exercise_type': 'read_aloud', 'duration_per_item': 90,
            'items': [
                {'id': 'a1', 'content': 'Ladies and gentlemen, welcome on board. On behalf of the entire crew, we ask that you please direct your attention to the flight attendants as we review the safety procedures for this flight. Please make sure your seat belt is fastened and your seat back and tray tables are in the full upright and locked position. There are six emergency exits on this aircraft. Please take a moment now to locate the exit nearest to you, keeping in mind that the nearest exit may be behind you.'}
            ]
        },
        {
            'id': 's_announcements', 'title': 'Part 3 — Cabin Announcements',
            'instruction': 'Press Play to hear each announcement, then repeat it as you would during an actual flight.',
            'exercise_type': 'repeat_sentence', 'duration_per_item': 30,
            'items': [
                {'id': 'r1', 'content': 'Ladies and gentlemen, we are beginning our descent into Mumbai.'},
                {'id': 'r2', 'content': 'For safety reasons, please ensure all electronic devices are switched off.'},
                {'id': 'r3', 'content': 'The local time at our destination is three forty-five in the afternoon.'},
                {'id': 'r4', 'content': 'Please fasten your seatbelts as we are experiencing some turbulence.'},
                {'id': 'r5', 'content': 'We would like to welcome our Business Class passengers to use the priority lounge.'}
            ]
        },
        {
            'id': 's_qa', 'title': 'Part 4 — Scenario Questions',
            'instruction': 'Answer each scenario question as you would during an actual flight. You have 60 seconds.',
            'exercise_type': 'qa_verbal', 'duration_per_item': 60,
            'items': '__OLLAMA__'
        },
        {
            'id': 's_topic', 'title': 'Part 5 — Topic Speaking',
            'instruction': 'Choose one topic and speak about it for 60 seconds.',
            'exercise_type': 'topic_speaking', 'duration_per_item': 60,
            'items': [
                {'id': 't1', 'content': 'How to handle a nervous or anxious passenger'},
                {'id': 't2', 'content': 'The qualities of an excellent cabin crew member'},
                {'id': 't3', 'content': 'Maintaining composure during an in-flight emergency'},
                {'id': 't4', 'content': 'What excellent in-flight customer service looks like'}
            ]
        }
    ],
    'edu_teaching_demo': [
        {
            'id': 's_vocab', 'title': 'Part 1 — Teaching Vocabulary',
            'instruction': 'Read each education term clearly. These are concepts you will use in your teaching role.',
            'exercise_type': 'vocabulary', 'duration_per_item': 8,
            'items': [
                {'id': 'w1', 'content': 'pedagogy'}, {'id': 'w2', 'content': 'curriculum'},
                {'id': 'w3', 'content': 'differentiation'}, {'id': 'w4', 'content': 'metacognition'},
                {'id': 'w5', 'content': 'scaffolding'}, {'id': 'w6', 'content': 'formative assessment'},
                {'id': 'w7', 'content': 'summative assessment'}, {'id': 'w8', 'content': 'constructivism'}
            ]
        },
        {
            'id': 's_explain', 'title': 'Part 2 — Explanation Passage',
            'instruction': 'Read the following passage aloud as if explaining it to a classroom of students.',
            'exercise_type': 'read_aloud', 'duration_per_item': 75,
            'items': [
                {'id': 'p1', 'content': 'The water cycle is a continuous process that describes how water moves through the environment. It begins with evaporation, where heat from the sun causes water from oceans, lakes, and rivers to turn into water vapour and rise into the atmosphere. As this vapour cools, it condenses to form clouds through a process called condensation. When enough water collects in the clouds, it falls back to Earth as precipitation — such as rain, snow, or hail. The cycle then begins again as this water flows back into our water bodies or soaks into the ground.'}
            ]
        },
        {
            'id': 's_qa', 'title': 'Part 3 — Teaching Scenario Questions',
            'instruction': 'Answer each question as an experienced teacher would. You have 60 seconds per question.',
            'exercise_type': 'qa_verbal', 'duration_per_item': 60,
            'items': '__OLLAMA__'
        },
        {
            'id': 's_topic', 'title': 'Part 4 — Mini Teaching Demo',
            'instruction': 'Choose a topic and explain it to an imaginary class for 90 seconds. Be clear, engaging, and structured.',
            'exercise_type': 'topic_speaking', 'duration_per_item': 90,
            'items': [
                {'id': 't1', 'content': 'Explain photosynthesis to 8th grade students'},
                {'id': 't2', 'content': 'Teach compound interest to college students'},
                {'id': 't3', 'content': 'Explain Newton\'s First Law to high school students'},
                {'id': 't4', 'content': 'Describe the causes of World War I to 10th grade students'}
            ]
        }
    ]
}

VOICE_SCENARIO_ITEMS: Dict[str, List[Dict]] = {
    'bpo_cust_handling': [
        {'id': 'sc1', 'content': 'A customer is calling angrily because they received the wrong product. They are demanding an immediate refund and threatening to leave a negative review. How do you handle this call?', 'context': 'Angry Customer — Wrong Delivery'},
        {'id': 'sc2', 'content': 'A customer says they have been waiting 45 minutes on hold and are very frustrated. They want to know why response times are so poor. How do you respond?', 'context': 'Long Wait Time Complaint'},
        {'id': 'sc3', 'content': 'A customer calls about a billing error where they were charged twice for the same service. They want it fixed immediately. Walk through how you would resolve this.', 'context': 'Billing Error — Duplicate Charge'},
        {'id': 'sc4', 'content': 'A customer believes they should have received a 50% discount on their order that they did not get. How do you explain the offer terms while keeping them satisfied?', 'context': 'Promotion Misunderstanding'},
    ],
    'bpo_objection_handling': [
        {'id': 'o1', 'content': 'A prospect says "Your product is too expensive compared to competitors." How do you overcome this price objection?', 'context': 'Price Objection'},
        {'id': 'o2', 'content': 'A customer says "I need to think about it and will get back to you." How do you keep them engaged without being pushy?', 'context': 'Think It Over Objection'},
        {'id': 'o3', 'content': 'A prospect says "I\'m already using a competitor and I\'m satisfied with them." How do you position your offering as a better alternative?', 'context': 'Competitor Loyalty Objection'},
    ],
    'bpo_call_quality': [
        {'id': 'cq1', 'content': 'You are reviewing a call where the agent spoke very quickly, used technical jargon, and frequently interrupted the customer. What specific feedback would you give this agent?', 'context': 'Call Quality Review'},
        {'id': 'cq2', 'content': 'A customer has escalated a complaint saying the previous agent was dismissive and did not resolve their issue. How do you handle this escalated call?', 'context': 'Escalated Call Handling'},
        {'id': 'cq3', 'content': 'A customer is becoming increasingly upset despite your best efforts. Describe exactly how you would de-escalate and bring the conversation to a positive resolution.', 'context': 'De-escalation Scenario'},
    ],
    'sales_video_pitch': [
        {'id': 'p1', 'content': 'You have 60 seconds to pitch a new cloud-based project management tool to a small business owner. Key benefits: saves 5 hours/week, reduces email by 60%, 5-minute setup. Pitch it now.', 'context': 'Product Pitch — Project Management Tool'},
        {'id': 'p2', 'content': 'Pitch a term life insurance product to a 35-year-old with young children and no existing life cover. Make it compelling in under 60 seconds.', 'context': 'Insurance Sales Pitch'},
        {'id': 'p3', 'content': 'A potential client says they are happy with their current vendor. Pitch why they should switch to you in under 60 seconds.', 'context': 'Competitive Switch Pitch'},
    ],
    'sales_objection_sim': [
        {'id': 'os1', 'content': 'The buyer says: "I don\'t have the budget right now." Respond with a rebuttal that acknowledges their concern and redirects to value.', 'context': 'Budget Objection'},
        {'id': 'os2', 'content': 'The buyer says: "I need to involve my team in this decision." How do you keep the deal moving forward without losing momentum?', 'context': 'Multi-Stakeholder Delay'},
        {'id': 'os3', 'content': 'The buyer says: "Your product seems complicated to set up." Reassure them and overcome this concern.', 'context': 'Complexity Concern'},
    ],
    'sales_lead_conv': [
        {'id': 'lc1', 'content': 'A lead downloaded your free trial but hasn\'t activated it in 5 days. You are calling them now. What do you say to move them forward?', 'context': 'Cold Lead Re-engagement'},
        {'id': 'lc2', 'content': 'A warm lead said "we might be interested in 3 months." How do you qualify them further and keep them in the pipeline?', 'context': 'Lead Qualification — Delayed Decision'},
        {'id': 'lc3', 'content': 'A lead asks 3 detailed technical questions during a discovery call. How do you answer while steering toward a trial or demo commitment?', 'context': 'Feature-Driven Lead'},
        {'id': 'lc4', 'content': 'A lead you have been nurturing for 2 weeks suddenly stops responding to emails. What is your re-engagement approach?', 'context': 'Silent Lead Recovery'},
    ],
    'sales_empathy': [
        {'id': 'se1', 'content': 'A long-term customer calls upset because a product they trusted failed to deliver the promised results. They feel let down. How do you respond empathetically and rebuild the relationship?', 'context': 'Disappointed Long-Term Customer'},
        {'id': 'se2', 'content': 'A customer mentions a personal hardship while calling for support. How do you balance professionalism with genuine empathy?', 'context': 'Emotionally Distressed Customer'},
        {'id': 'se3', 'content': 'A customer is frustrated because they feel a previous agent did not listen to them. How do you demonstrate from the very start that you are genuinely listening?', 'context': 'Feeling Unheard'},
    ],
    'hc_communication': [
        {'id': 'hc1', 'content': 'A patient is anxious about an upcoming procedure and keeps asking "Will it hurt?" How do you communicate with them in a calm, honest, and reassuring way?', 'context': 'Pre-Procedure Patient Anxiety'},
        {'id': 'hc2', 'content': 'A patient\'s family member is demanding immediate updates on the patient\'s condition but you cannot share details without consent. How do you handle this?', 'context': 'Confidentiality — Family Inquiry'},
        {'id': 'hc3', 'content': 'An elderly patient does not understand their discharge instructions. How do you ensure they leave with a clear understanding of their follow-up care?', 'context': 'Patient Education — Discharge'},
    ],
    'hc_case_handling': [
        {'id': 'ch1', 'content': 'A patient deteriorates unexpectedly during your shift. You need to coordinate with the senior nurse, doctor, and family simultaneously. Describe how you handle the next 5 minutes.', 'context': 'Patient Deterioration Scenario'},
        {'id': 'ch2', 'content': 'You receive information about a patient who missed their follow-up appointment for a serious condition and is now unreachable. What steps do you take?', 'context': 'Missed Critical Follow-Up'},
        {'id': 'ch3', 'content': 'Two patients need attention at the same time — one is in mild pain and one is having difficulty breathing. How do you prioritize and respond?', 'context': 'Multi-Patient Prioritization'},
    ],
    'retail_video_test': [
        {'id': 'rv1', 'content': 'A customer enters your store looking confused and unsure. They don\'t approach the counter. How do you greet them and initiate engagement naturally?', 'context': 'Floor Greeting & Approach'},
        {'id': 'rv2', 'content': 'A customer is trying on clothes and asks for your honest opinion between two options. How do you give helpful advice without being pushy?', 'context': 'Product Recommendation'},
        {'id': 'rv3', 'content': 'A customer is about to leave without buying. They say "I\'ll think about it." How do you respond to increase the chance of a sale without applying pressure?', 'context': 'Exit Conversation'},
    ],
    'retail_complaint': [
        {'id': 'rc1', 'content': 'A customer returns a product claiming it was defective from day one. They are upset and want a full refund plus compensation. How do you handle this?', 'context': 'Defective Product Return'},
        {'id': 'rc2', 'content': 'A customer complains loudly on the store floor that the staff ignored them. Other shoppers can hear. How do you manage this situation?', 'context': 'Public Complaint in Store'},
        {'id': 'rc3', 'content': 'A customer says a promotional price they saw online is not being honored at your store. Store policy says prices may differ. How do you resolve this?', 'context': 'Price Mismatch Dispute'},
    ],
    'av_passenger': [
        {'id': 'ap1', 'content': 'A passenger is extremely nervous about flying and shows signs of panic during boarding. How do you calmly manage the situation and ensure they board comfortably?', 'context': 'Nervous Passenger — Pre-Flight'},
        {'id': 'ap2', 'content': 'Two passengers have a dispute over seating mid-flight and the argument is becoming disruptive. How do you de-escalate the situation?', 'context': 'In-Flight Passenger Conflict'},
        {'id': 'ap3', 'content': 'A passenger says they need special assistance but did not pre-arrange it. The flight is about to depart. How do you handle this with minimal disruption?', 'context': 'Unannounced Special Assistance'},
    ],
    'edu_delivery': [
        {'id': 'ed1', 'content': 'You are mid-lesson and notice half the class is visibly disengaged. What do you do in the next 2 minutes to recapture their attention without stopping the lesson entirely?', 'context': 'Class Disengagement'},
        {'id': 'ed2', 'content': 'A student asks a question you genuinely do not know the answer to, in front of the whole class. How do you handle this professionally?', 'context': 'Unknown Answer in Class'},
        {'id': 'ed3', 'content': 'You are explaining a concept and one student says "I still don\'t understand" while the others seem to get it. How do you differentiate without losing the rest of the class?', 'context': 'Student Comprehension Gap'},
        {'id': 'ed4', 'content': 'Describe how you would structure the first 5 minutes of a new lesson to maximise student engagement and retention.', 'context': 'Lesson Opening Structure'},
    ],
}

TEXT_WRITING_SECTIONS: Dict[str, List[Dict]] = {
    'gen_resume_quiz': [
        {
            'id': 's_resume_summary', 'title': 'Professional Summary',
            'instruction': 'Write a compelling 3-5 sentence professional summary for the role described. Focus on your key strengths, years of experience, and what value you bring.',
            'exercise_type': 'text_response', 'format_hint': 'Keep it concise (50-80 words). Write in first person. Avoid generic phrases like "hard-working team player".',
            'duration_per_item': 300,
            'items': [
                {'id': 'rs1', 'content': 'Write a professional summary for a candidate applying for a Customer Service Executive role at a BPO. The candidate has 2 years of experience in voice support and has handled 80+ calls per day.'},
                {'id': 'rs2', 'content': 'Write a professional summary for a fresher applying for a Data Analyst internship. They have completed a Python and SQL course and built a sales dashboard project during college.'},
            ]
        },
        {
            'id': 's_resume_achievements', 'title': 'Achievement Statements',
            'instruction': 'Rewrite the weak resume bullet points below into strong achievement statements using the format: Action Verb + Task + Result/Impact (quantified where possible).',
            'exercise_type': 'text_response', 'format_hint': 'Start with a strong action verb. Add numbers or percentages where you can. Focus on outcomes, not just duties.',
            'duration_per_item': 240,
            'items': [
                {'id': 'ra1', 'content': 'Weak bullet: "Responsible for handling customer complaints."\n\nRewrite this as a strong, quantified achievement statement.'},
                {'id': 'ra2', 'content': 'Weak bullet: "Did social media posts for the company."\n\nRewrite this as a strong, quantified achievement statement.'},
            ]
        },
    ],
    'gen_typing': [
        {
            'id': 's_typing', 'title': 'Typing Accuracy Test',
            'instruction': 'Type the passage below exactly as shown. Accuracy and speed both matter. Do not copy-paste.',
            'exercise_type': 'text_response', 'format_hint': 'Type the passage exactly — including punctuation and capitalisation.',
            'duration_per_item': 120,
            'items': [
                {'id': 't1', 'content': 'The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. How vexingly quick daft zebras jump! The five boxing wizards jump quickly. Sphinx of black quartz, judge my vow.'},
                {'id': 't2', 'content': 'Effective communication is the foundation of every successful professional relationship. When writing emails or reports, clarity and brevity are equally important. Always proofread your work before sending, and ensure that your message conveys the intended meaning without ambiguity.'},
            ]
        },
    ],
    'bpo_chat_email_etiquette': [
        {
            'id': 's_email', 'title': 'Email Writing',
            'instruction': 'Write a professional email response for each scenario. Include subject line, greeting, body, and sign-off.',
            'exercise_type': 'text_response', 'format_hint': 'Subject: … | Greeting | Body (2-3 paragraphs) | Closing',
            'duration_per_item': 300,
            'items': [
                {'id': 'e1', 'content': 'A customer emails to say their online order was delivered to the wrong address. They want either a re-delivery or a full refund. Write a professional email response.'},
                {'id': 'e2', 'content': 'A client is following up on a refund requested 7 days ago that has not been processed. They are getting impatient. Write a professional email update.'},
            ]
        },
        {
            'id': 's_chat', 'title': 'Live Chat Responses',
            'instruction': 'Write a concise, professional live chat response. Keep it clear, empathetic, and within 2-3 sentences.',
            'exercise_type': 'text_response', 'format_hint': 'Brief (2-3 sentences) · Empathetic · Action-focused',
            'duration_per_item': 120,
            'items': [
                {'id': 'c1', 'content': 'Customer: "Hi, I\'ve been waiting 3 days for my tracking number. My order number is #45231. Can you help?"'},
                {'id': 'c2', 'content': 'Customer: "I want to cancel my subscription. I never use it and keep getting charged."'},
                {'id': 'c3', 'content': 'Customer: "The product I received is completely different from what was shown in the photo on your website."'},
            ]
        },
    ],
    'sales_creativity': [
        {
            'id': 's_copy', 'title': 'Ad Copy Writing',
            'instruction': 'Write creative marketing copy for each brief. Be persuasive, original, and engaging.',
            'exercise_type': 'text_response', 'format_hint': 'Include a tagline + 3-4 sentence description. Creative and compelling.',
            'duration_per_item': 300,
            'items': [
                {'id': 'ad1', 'content': 'Write ad copy for a new energy drink called "Surge" targeting working professionals aged 25-35. Key benefits: natural energy boost, no crash, great taste.'},
                {'id': 'ad2', 'content': 'Write a social media post for a budget airline launching a new Mumbai–Dubai route. Angle: affordable luxury travel.'},
            ]
        },
        {
            'id': 's_campaign', 'title': 'Campaign Concept',
            'instruction': 'Write a brief marketing campaign concept for the given brief.',
            'exercise_type': 'text_response', 'format_hint': 'Include: Campaign theme · Target audience · Key message · 2-3 tactics',
            'duration_per_item': 420,
            'items': [
                {'id': 'ca1', 'content': 'A new app helps working parents manage their children\'s school schedule, homework reminders, and teacher communication in one place. Design a digital marketing campaign to reach busy parents in Indian metros.'},
            ]
        },
    ],
    'con_project_coord': [
        {
            'id': 's_scenarios', 'title': 'Project Coordination Scenarios',
            'instruction': 'Write your response to each coordination challenge. Be specific about steps, timelines, and communication actions.',
            'exercise_type': 'text_response', 'format_hint': 'Be specific: Actions · Timelines · Communication plan',
            'duration_per_item': 360,
            'items': [
                {'id': 'pc1', 'content': 'You discover structural steel delivery will be delayed by 2 weeks, directly affecting 3 dependent tasks. Write a coordination plan to minimise the project timeline impact.'},
                {'id': 'pc2', 'content': 'Two subcontractors both need to work in the same area on the same day and neither can move. Write a resolution plan with alternative scheduling options.'},
                {'id': 'pc3', 'content': 'The client has requested a significant design change mid-project. Write a change request communication outlining the impact on cost, timeline, and resources.'},
            ]
        },
    ],
    'con_blueprint': [
        {
            'id': 's_reading', 'title': 'Blueprint Interpretation',
            'instruction': 'Read each blueprint scenario and write your interpretation or answer. Show calculations where relevant.',
            'exercise_type': 'text_response', 'format_hint': 'Show your reasoning clearly. Include calculations where relevant.',
            'duration_per_item': 300,
            'items': [
                {'id': 'bp1', 'content': 'A structural drawing shows a column labelled "300 × 300 R.C.C." at 1:50 scale, using ⊕ for structural columns and N.T.S for non-structural elements. Answer: (a) Actual column dimensions? (b) What does ⊕ indicate? (c) What does N.T.S mean?'},
                {'id': 'bp2', 'content': 'A floor plan shows a room measuring 4.5m × 6m with a window opening of 1200mm and 600mm wall returns on each side. Calculate: (a) Room area in sq. metres. (b) Total window + return width. (c) Wall remaining on each side if total room width is 4500mm.'},
                {'id': 'bp3', 'content': 'A section drawing notes: "150 THK R.C.C SLAB, 12mm DIA @ 150 C/C BOTH WAYS." Explain what each part of this notation means.'},
            ]
        },
    ],
}

CODING_PROBLEMS: Dict[str, List[Dict]] = {
    'gen_coding_basic': [
        {'id': 'p1', 'content': 'Write a function fizzbuzz(n) that returns a list of strings from 1 to n.\nRules:\n• "Fizz" if divisible by 3\n• "Buzz" if divisible by 5\n• "FizzBuzz" if divisible by both\n• The number as a string otherwise\n\nExample: fizzbuzz(15) → ["1","2","Fizz","4","Buzz","Fizz","7","8","Fizz","Buzz","11","Fizz","13","14","FizzBuzz"]', 'language': 'python', 'starter_code': 'def fizzbuzz(n):\n    # Your code here\n    pass\n\nprint(fizzbuzz(15))'},
        {'id': 'p2', 'content': 'Write a function reverse_string(s) that returns the string reversed WITHOUT using built-in reverse methods.\n\nExamples:\n  reverse_string("hello")  → "olleh"\n  reverse_string("Python") → "nohtyP"', 'language': 'python', 'starter_code': 'def reverse_string(s):\n    # Do NOT use s[::-1] or reversed()\n    pass\n\nprint(reverse_string("hello"))   # olleh\nprint(reverse_string("Python"))  # nohtyP'},
        {'id': 'p3', 'content': 'Write a function find_duplicates(lst) that returns a list of all numbers that appear more than once.\n\nExamples:\n  find_duplicates([1, 2, 3, 2, 4, 3, 5]) → [2, 3]\n  find_duplicates([1, 2, 3])              → []', 'language': 'python', 'starter_code': 'def find_duplicates(lst):\n    # Your code here\n    pass\n\nprint(find_duplicates([1, 2, 3, 2, 4, 3, 5]))  # [2, 3]\nprint(find_duplicates([1, 2, 3]))               # []'},
    ],
    'it_adv_coding': [
        {'id': 'p1', 'content': 'Implement max_subarray_sum(nums) using Kadane\'s Algorithm.\nFind the maximum sum of any contiguous subarray.\n\nExample:\n  Input:  [-2, 1, -3, 4, -1, 2, 1, -5, 4]\n  Output: 6  (subarray [4, -1, 2, 1])\n\nExpected: O(n) time, O(1) space.', 'language': 'python', 'starter_code': 'from typing import List\n\ndef max_subarray_sum(nums: List[int]) -> int:\n    # Your code here\n    pass\n\nprint(max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]))  # Expected: 6'},
        {'id': 'p2', 'content': 'Implement valid_parentheses(s: str) -> bool.\nReturn True if every bracket has a matching closing bracket in the correct order.\n\nBracket pairs: () [] {}\n\nExamples:\n  "({[]})"  → True\n  "({)}"    → False', 'language': 'python', 'starter_code': 'def valid_parentheses(s: str) -> bool:\n    # Your code here\n    pass\n\nprint(valid_parentheses("({[]})"))  # True\nprint(valid_parentheses("({)}"))    # False'},
        {'id': 'p3', 'content': 'Implement two_sum(nums, target) returning indices of two numbers that add to target.\n\nExample:\n  nums = [2, 7, 11, 15], target = 9\n  Output: [0, 1]\n\nExpected: O(n) time using a hash map.', 'language': 'python', 'starter_code': 'from typing import List\n\ndef two_sum(nums: List[int], target: int) -> List[int]:\n    # Your code here\n    pass\n\nprint(two_sum([2, 7, 11, 15], 9))  # [0, 1]'},
    ],
    'it_algorithmic_thinking': [
        {'id': 'p1', 'content': 'Write fibonacci(n) using dynamic programming (not recursion).\nReturn the nth Fibonacci number. F(0)=0, F(1)=1, F(10)=55.\n\nExpected: O(n) time, O(1) space.', 'language': 'python', 'starter_code': 'def fibonacci(n: int) -> int:\n    # Use DP, not recursion\n    pass\n\nprint(fibonacci(10))  # 55'},
        {'id': 'p2', 'content': 'Implement binary_search(arr, target) on a sorted array.\nReturn index of target or -1 if not found.\n\nExpected: O(log n) time.', 'language': 'python', 'starter_code': 'from typing import List\n\ndef binary_search(arr: List[int], target: int) -> int:\n    # Your code here\n    pass\n\nprint(binary_search([1, 3, 5, 7, 9, 11], 7))  # 3\nprint(binary_search([1, 3, 5], 4))             # -1'},
        {'id': 'p3', 'content': 'Implement merge_sorted_arrays(a, b) merging two sorted arrays into one sorted array.\n\nExpected: O(n+m) time.\n\nExample: [1,3,5] + [2,4,6] → [1,2,3,4,5,6]', 'language': 'python', 'starter_code': 'from typing import List\n\ndef merge_sorted_arrays(a: List[int], b: List[int]) -> List[int]:\n    # Your code here\n    pass\n\nprint(merge_sorted_arrays([1, 3, 5], [2, 4, 6]))'},
    ],
    'it_debugging': [
        {'id': 'p1', 'content': 'Find and fix ALL bugs in this function:\n\n```python\ndef calculate_average(numbers):\n    total = 0\n    for num in numbers\n        total += num\n    average = total / len(numbers)\n    print("Average:", average)\n    return\n```\n\nThere are 3 bugs. Rewrite the corrected version below.', 'language': 'python', 'starter_code': '# Write the CORRECTED version:\ndef calculate_average(numbers):\n    # Fix all bugs here\n    pass\n\nprint(calculate_average([10, 20, 30]))  # Should print Average: 20.0 and return 20.0\nprint(calculate_average([]))           # Should handle empty list gracefully'},
        {'id': 'p2', 'content': 'The following JavaScript function should count word occurrences but has a bug:\n\n```javascript\nfunction wordCount(str) {\n    const words = str.split(" ");\n    const count = {};\n    for (let word in words) {\n        if (count[word]) count[word]++;\n        else count[word] = 1;\n    }\n    return count;\n}\n```\n\n1. Identify the bug in a comment.\n2. Write the corrected function.', 'language': 'javascript', 'starter_code': '// 1. Bug:\n// \n\n// 2. Corrected function:\nfunction wordCount(str) {\n    // Your fix here\n}\n\nconsole.log(wordCount("hello world hello"));  // { hello: 2, world: 1 }'},
    ],
    'it_sql_pro': [
        {'id': 'q1', 'content': 'Find the top 5 customers by total purchase amount.\n\nTables:\n  orders(order_id, customer_id, total_amount, order_date)\n  customers(customer_id, name, email)\n\nReturn: name, email, total_spent — ordered by total_spent DESC', 'language': 'sql', 'starter_code': '-- Top 5 customers by total purchase amount\nSELECT\n    \nFROM\n    \nJOIN\n    \nGROUP BY\n    \nORDER BY\n    \nLIMIT 5;'},
        {'id': 'q2', 'content': 'Find customers who placed at least 2 orders in the past 30 days but NO orders in the current calendar month.\n\nTable: orders(order_id, customer_id, order_date, total_amount)', 'language': 'sql', 'starter_code': '-- Customers: 2+ orders last 30 days, none this month\nSELECT DISTINCT customer_id\nFROM orders\nWHERE\n    '},
        {'id': 'q3', 'content': 'Calculate running total of sales by date.\n\nTable: sales(sale_id, sale_date, amount)\n\nReturn: sale_date, daily_total, running_total — ordered by sale_date ASC\n\nHint: Use window functions (SUM OVER).', 'language': 'sql', 'starter_code': '-- Running total of sales by date\nSELECT\n    sale_date,\n    SUM(amount) AS daily_total,\n    -- running_total column here\nFROM sales\nGROUP BY sale_date\nORDER BY sale_date;'},
        {'id': 'q4', 'content': 'Find products that have NEVER been ordered.\n\nTables:\n  products(product_id, name, price, category)\n  order_items(item_id, order_id, product_id, quantity)\n\nReturn: product_id, name, category', 'language': 'sql', 'starter_code': '-- Products never ordered\nSELECT p.product_id, p.name, p.category\nFROM products p\nWHERE\n    -- your condition here\n    ;'},
    ],
    'it_react_skills': [
        {'id': 'r1', 'content': 'Write a React functional component Counter that:\n• Displays a count starting at 0\n• Has Increment (+1) and Decrement (−1) buttons\n• Has a Reset button (back to 0)\n• Count cannot go below 0', 'language': 'jsx', 'starter_code': 'import React, { useState } from \'react\';\n\nfunction Counter() {\n    // Your state here\n    \n    return (\n        <div>\n            {/* Your JSX */}\n        </div>\n    );\n}\n\nexport default Counter;'},
        {'id': 'r2', 'content': 'Write a React component SearchList that:\n• Accepts prop items (array of strings)\n• Has a text input for filtering\n• Shows only items containing the search text (case-insensitive)\n• Shows count like "Showing 3 of 10 items"', 'language': 'jsx', 'starter_code': 'import React, { useState } from \'react\';\n\nfunction SearchList({ items }) {\n    // Your state here\n    \n    return (\n        <div>\n            {/* Search input + filtered list */}\n        </div>\n    );\n}\n\nexport default SearchList;'},
    ],
    'it_js_pro': [
        {'id': 'j1', 'content': 'Implement memoize(fn) that caches function results.\n\nBehaviour:\n  const fn = n => n * 2;\n  const mfn = memoize(fn);\n  mfn(5); // computes and caches\n  mfn(5); // returns cache, no recomputation\n  mfn(6); // computes new key', 'language': 'javascript', 'starter_code': 'function memoize(fn) {\n    // Your implementation\n}\n\nlet calls = 0;\nconst fn = n => { calls++; return n * 2; };\nconst mfn = memoize(fn);\nconsole.log(mfn(5), mfn(5), mfn(6)); // 10 10 12\nconsole.log("Calls:", calls);          // Should be 2'},
        {'id': 'j2', 'content': 'Implement deepEqual(a, b) for deep structural comparison.\n\nExamples:\n  deepEqual({a:1, b:{c:2}}, {a:1, b:{c:2}}) → true\n  deepEqual([1,[2,3]], [1,[2,4]])            → false\n  deepEqual(null, null)                      → true', 'language': 'javascript', 'starter_code': 'function deepEqual(a, b) {\n    // Your implementation\n}\n\nconsole.log(deepEqual({a:1,b:{c:2}}, {a:1,b:{c:2}})); // true\nconsole.log(deepEqual([1,[2,3]], [1,[2,4]]));           // false'},
    ],
    'it_system_design_lite': [
        {'id': 'sd1', 'content': 'Design a class structure for a Library Management System.\n\nRequirements:\n• Add/remove books\n• Register members (max 3 books borrowed at once)\n• Check out and return books\n• Search by title, author, or ISBN\n\nDefine classes, attributes, and key methods. Any language or pseudocode.', 'language': 'python', 'starter_code': '# Library Management System\n# Add comments explaining your design decisions\n\nclass Book:\n    def __init__(self, isbn, title, author):\n        pass\n\nclass Member:\n    def __init__(self, member_id, name):\n        pass\n\nclass Library:\n    def add_book(self, book): pass\n    def checkout(self, member_id, isbn): pass\n    def return_book(self, member_id, isbn): pass\n    def search(self, query): pass'},
    ],
    'it_system_design_pro': [
        {'id': 'sd1', 'content': 'Design a URL Shortener (like bit.ly)\n\nScale:\n• 100M URLs stored\n• 1,000 writes/sec, 10,000 reads/sec\n• Global, <100ms P99 latency\n• Short codes are permanent\n\nAddress:\n1. Core API endpoints\n2. Data model / schema\n3. Component architecture\n4. Caching strategy\n5. Short code generation (collision-resistant)', 'language': 'text', 'starter_code': '# URL Shortener System Design\n\n## 1. API Endpoints\n\n\n## 2. Data Model\n\n\n## 3. Component Architecture\n\n\n## 4. Caching Strategy\n\n\n## 5. Short Code Generation\n'},
    ],
    'tel_troubleshoot': [
        {'id': 'ts1', 'content': 'A customer cannot make outgoing calls but can receive them. Issue affects only their mobile, not their home phone on the same account.\n\nWrite a diagnostic procedure:\n1. 3 most likely root causes\n2. Steps to isolate the issue\n3. Resolution approach', 'language': 'text', 'starter_code': '## Diagnostic Procedure\n\n### Likely Root Causes\n1. \n2. \n3. \n\n### Isolation Steps\n1. \n2. \n3. \n\n### Resolution'},
        {'id': 'ts2', 'content': 'Network monitoring shows 30% packet loss on a backbone router in the south region, affecting 5,000 customers.\n\nDescribe your incident response:\n1. Immediate triage actions (first 5 minutes)\n2. Escalation path\n3. Customer communication plan\n4. Root cause analysis approach', 'language': 'text', 'starter_code': '## Incident Response\n\n### 1. Immediate Triage\n\n### 2. Escalation Path\n\n### 3. Customer Communication\n\n### 4. Root Cause Analysis'},
    ],
}

MCQ_FALLBACK: Dict[str, List[Dict]] = {
    'fin_awareness': [
        {'id': 'q1', 'content': 'What does RBI stand for?', 'options': ['Reserve Bank of India', 'Regional Banking Institution', 'Retail Banking Index', 'Revenue Bureau of India'], 'correct': 0},
        {'id': 'q2', 'content': 'Which of the following is NOT a function of RBI?', 'options': ['Issuing passports', 'Issuing currency notes', 'Regulating commercial banks', 'Managing foreign exchange reserves'], 'correct': 0},
        {'id': 'q3', 'content': 'What is NEFT used for?', 'options': ['Electronic fund transfers between bank accounts', 'Filing income tax returns', 'Credit score checking', 'Opening new accounts'], 'correct': 0},
        {'id': 'q4', 'content': 'What does CRR stand for?', 'options': ['Cash Reserve Ratio', 'Credit Reserve Rate', 'Central Reserve Requirement', 'Current Reserve Ratio'], 'correct': 0},
        {'id': 'q5', 'content': 'What is a Fixed Deposit?', 'options': ['A deposit held for a fixed period at a fixed interest rate', 'A daily savings account', 'A type of insurance product', 'A recurring debit scheme'], 'correct': 0},
    ],
    'fin_kyc_aml': [
        {'id': 'q1', 'content': 'What does KYC stand for?', 'options': ['Know Your Customer', 'Know Your Credit', 'Keep Your Credentials', 'Know Your Currency'], 'correct': 0},
        {'id': 'q2', 'content': 'Which is an AML red flag?', 'options': ['Large unexplained cash deposits', 'Monthly salary deposit', 'Opening a savings account', 'Standard wire transfer from employer'], 'correct': 0},
        {'id': 'q3', 'content': 'What is the purpose of a Suspicious Activity Report (SAR)?', 'options': ['Report suspicious financial activity to regulators', 'Report customer complaints', 'Close a customer account', 'Request identity documents'], 'correct': 0},
        {'id': 'q4', 'content': 'In AML, "structuring" means:', 'options': ['Breaking large transactions into smaller ones to avoid reporting thresholds', 'Organising financial statements', 'Creating corporate structures', 'Scheduling recurring payments'], 'correct': 0},
    ],
    'mfg_safety': [
        {'id': 'q1', 'content': 'What does PPE stand for?', 'options': ['Personal Protective Equipment', 'Production Process Engineering', 'Plant Preventive Equipment', 'Process Performance Evaluation'], 'correct': 0},
        {'id': 'q2', 'content': 'First action if you spot a chemical spill on the factory floor?', 'options': ['Alert colleagues and follow emergency spill procedure', 'Clean it yourself immediately', 'Ignore small spills', 'Report at end of shift'], 'correct': 0},
        {'id': 'q3', 'content': 'What is Lockout-Tagout (LOTO) used for?', 'options': ['Safely de-energize machines before maintenance', 'Secure storage cabinets', 'Track production output', 'Verify material quality'], 'correct': 0},
        {'id': 'q4', 'content': 'A Safety Data Sheet (SDS) provides information about:', 'options': ['Hazardous chemicals and safe handling', 'Employee shift schedules', 'Quality control metrics', 'Production targets'], 'correct': 0},
    ],
    'av_safety': [
        {'id': 'q1', 'content': 'Primary purpose of a pre-flight safety demonstration?', 'options': ['Inform passengers about emergency procedures', 'Entertain passengers during boarding', 'Check seat assignments', 'Explain menu options'], 'correct': 0},
        {'id': 'q2', 'content': 'When must tray tables be stowed?', 'options': ['During takeoff and landing', 'Only during landing', 'Only above 10,000 feet', 'May remain open at any time'], 'correct': 0},
        {'id': 'q3', 'content': 'What is the brace position?', 'options': ['Protective body position for emergency landings', 'Standard takeoff stance for crew', 'A position for turbulence', 'Crew standing position during boarding'], 'correct': 0},
        {'id': 'q4', 'content': 'Oxygen masks in cabin deploy automatically at approximately:', 'options': ['14,000 feet (reduced cabin pressure)', '35,000 feet regardless', 'Only when crew manually activate them', 'Only in declared emergencies'], 'correct': 0},
    ],
    'av_terminology': [
        {'id': 'q1', 'content': 'What does IATA stand for?', 'options': ['International Air Transport Association', 'International Airline Terminal Authority', 'International Aviation Training Agency', 'Intercontinental Air Traffic Authority'], 'correct': 0},
        {'id': 'q2', 'content': 'What is a "turnaround" in aviation?', 'options': ['Preparing aircraft for the next flight after landing', 'Aircraft turning around mid-flight', 'A cancelled and rescheduled flight', 'A maintenance overhaul'], 'correct': 0},
        {'id': 'q3', 'content': 'What does PAX refer to in aviation?', 'options': ['Passengers', 'Package freight', 'Parking area index', 'Pilot axis coordinate'], 'correct': 0},
        {'id': 'q4', 'content': 'ETA means?', 'options': ['Estimated Time of Arrival', 'Emergency Terminal Alert', 'Exit Tracking Authorization', 'Expected Terminal Approach'], 'correct': 0},
        {'id': 'q5', 'content': 'In ICAO phonetic alphabet, Alpha represents?', 'options': ['The letter A', 'The letter H', 'Altitude', 'Arrival'], 'correct': 0},
    ],
    'con_site_safety': [
        {'id': 'q1', 'content': 'What does OSHA stand for?', 'options': ['Occupational Safety and Health Administration', 'Onsite Safety and Hazard Assessment', 'Operational Standards and Hazard Authority', 'Open Site Health Agreement'], 'correct': 0},
        {'id': 'q2', 'content': 'Fall protection required at height of:', 'options': ['6 feet (1.8m) or more', 'Only above 10 feet', 'Only during roof work', 'Optional for experienced workers'], 'correct': 0},
        {'id': 'q3', 'content': 'What is a Toolbox Talk?', 'options': ['Brief safety meeting before starting work', 'Tool inventory review', 'New worker training only', 'Project cost review'], 'correct': 0},
        {'id': 'q4', 'content': 'Color for WARNING signs on construction sites?', 'options': ['Yellow', 'Red', 'Green', 'Blue'], 'correct': 0},
    ],
    'hc_terminology': [
        {'id': 'q1', 'content': 'Medical abbreviation PRN means?', 'options': ['As needed', 'Per regular norm', 'Prescribed route now', 'Patient requires nutrition'], 'correct': 0},
        {'id': 'q2', 'content': 'NPO in clinical context means?', 'options': ['Nothing by mouth', 'No prior operations', 'Night patient observation', 'Normal physiological output'], 'correct': 0},
        {'id': 'q3', 'content': 'Hypertension refers to?', 'options': ['High blood pressure', 'Low blood pressure', 'Elevated heart rate', 'Fluid overload'], 'correct': 0},
        {'id': 'q4', 'content': 'The trachea carries?', 'options': ['Air from throat to lungs', 'Food to stomach', 'Filters blood', 'Regulates temperature'], 'correct': 0},
        {'id': 'q5', 'content': 'ECG (EKG) measures?', 'options': ['Electrical activity of the heart', 'Brain activity', 'Lung capacity', 'Blood glucose'], 'correct': 0},
    ],
    'hc_ethics': [
        {'id': 'q1', 'content': 'Informed consent means?', 'options': ['Patient voluntarily agrees to treatment after being fully informed', 'Doctor agrees to treat a patient', 'Insurance pre-authorization', 'Family approval for a procedure'], 'correct': 0},
        {'id': 'q2', 'content': 'Non-maleficence means?', 'options': ['Do no harm', 'Act in patient\'s best interest', 'Treat all patients equally', 'Respect patient autonomy'], 'correct': 0},
        {'id': 'q3', 'content': 'A competent patient refuses a life-saving procedure. You should?', 'options': ['Respect their decision — they have the right to refuse', 'Proceed to save their life', 'Get family consent to override', 'Seek a court order immediately'], 'correct': 0},
        {'id': 'q4', 'content': 'Patient confidentiality means?', 'options': ['Information cannot be shared without consent except in legally defined situations', 'Records shared with all hospital staff', 'Information shared with family automatically', 'Records must be digital and shared on request'], 'correct': 0},
    ],
    'log_inventory': [
        {'id': 'q1', 'content': 'What is a SKU?', 'options': ['Unique identifier for each distinct product in inventory', 'Storage area in a warehouse', 'Shipping label format', 'Unit of warehouse floor space'], 'correct': 0},
        {'id': 'q2', 'content': 'FIFO stands for?', 'options': ['First In, First Out', 'Fast Item Flow Out', 'Flexible Inventory Follow-through', 'Forward Inventory Order'], 'correct': 0},
        {'id': 'q3', 'content': 'Safety stock is?', 'options': ['Extra inventory held to prevent stockouts during unexpected demand or supply delays', 'Minimum stock before re-ordering', 'Damaged goods stored separately', 'Stock reserved for safety equipment'], 'correct': 0},
        {'id': 'q4', 'content': 'A negative variance in an inventory audit indicates?', 'options': ['Less physical stock than system records (possible shrinkage or error)', 'More stock than expected', 'Accurate count', 'Software error'], 'correct': 0},
    ],
    'tel_network': [
        {'id': 'q1', 'content': 'IP stands for?', 'options': ['Internet Protocol', 'Internal Processing', 'Index Protocol', 'Interface Program'], 'correct': 0},
        {'id': 'q2', 'content': 'A router\'s primary function is?', 'options': ['Forwarding packets between different networks', 'Connecting devices within same LAN only', 'Amplifying wireless signals', 'Storing DNS records'], 'correct': 0},
        {'id': 'q3', 'content': 'DNS stands for?', 'options': ['Domain Name System', 'Data Network Service', 'Dynamic Network Setup', 'Direct Name Server'], 'correct': 0},
        {'id': 'q4', 'content': 'TCP vs UDP key difference?', 'options': ['TCP is connection-oriented and reliable; UDP is connectionless and faster', 'TCP is faster but less reliable', 'UDP requires handshake; TCP does not', 'They are identical'], 'correct': 0},
    ],
    'sales_digital_mcq': [
        {'id': 'q1', 'content': 'CTR stands for?', 'options': ['Click-Through Rate', 'Customer Total Revenue', 'Content Traffic Reach', 'Conversion Tracking Report'], 'correct': 0},
        {'id': 'q2', 'content': 'A/B testing is used for?', 'options': ['Comparing two content versions to see which performs better', 'Testing internet speed on two devices', 'Morning vs evening campaign timing', 'Testing two budget levels'], 'correct': 0},
        {'id': 'q3', 'content': 'CPC stands for?', 'options': ['Cost Per Click', 'Customer Purchase Conversion', 'Content Per Campaign', 'Click Page Conversion'], 'correct': 0},
        {'id': 'q4', 'content': 'SEO stands for?', 'options': ['Search Engine Optimization', 'Social Engagement Objective', 'Sponsored Engagement Option', 'Site Engagement Overview'], 'correct': 0},
        {'id': 'q5', 'content': '10,000 impressions, 200 clicks — CTR is?', 'options': ['2%', '20%', '0.2%', '5%'], 'correct': 0},
    ],
    'fin_reasoning': [
        {'id': 'q1', 'content': 'Simple interest on ₹10,000 at 8% p.a. for 3 years?', 'options': ['₹2,400', '₹2,000', '₹800', '₹3,000'], 'correct': 0},
        {'id': 'q2', 'content': 'Product costing ₹500 sold at 20% profit. Selling price?', 'options': ['₹600', '₹550', '₹520', '₹580'], 'correct': 0},
        {'id': 'q3', 'content': '15% of 240 equals?', 'options': ['36', '24', '30', '48'], 'correct': 0},
        {'id': 'q4', 'content': '₹1,000 at 10% compounded annually — amount after 2 years?', 'options': ['₹1,210', '₹1,200', '₹1,100', '₹1,150'], 'correct': 0},
    ],
    'edu_subject_knowledge': [
        {'id': 'q1', 'content': 'During osmosis, water moves from?', 'options': ['Lower solute concentration to higher', 'Higher solute to lower', 'Any direction based on temperature', 'Only through non-living membranes'], 'correct': 0},
        {'id': 'q2', 'content': 'In A = P(1 + r/n)^(nt), what is n?', 'options': ['Times interest is compounded per year', 'Number of years', 'Principal amount', 'Rate of interest'], 'correct': 0},
        {'id': 'q3', 'content': 'Newton\'s Second Law states?', 'options': ['F = ma (Force = Mass × Acceleration)', 'Every action has an equal and opposite reaction', 'Object at rest stays at rest', 'Momentum is conserved in all systems'], 'correct': 0},
        {'id': 'q4', 'content': 'Photosynthesis occurs in?', 'options': ['Chloroplasts', 'Mitochondria', 'Nucleus', 'Ribosomes'], 'correct': 0},
        {'id': 'q5', 'content': 'Chemical symbol for gold?', 'options': ['Au', 'Go', 'Gd', 'Ag'], 'correct': 0},
    ],
    'edu_classroom_mgmt': [
        {'id': 'q1', 'content': 'Most effective way to regain attention in a noisy classroom?', 'options': ['Calm consistent signal the class recognises', 'Shout over the noise', 'Ignore it and continue', 'Send disruptive students out immediately'], 'correct': 0},
        {'id': 'q2', 'content': 'A student disrupts class repeatedly. Best practice?', 'options': ['Address privately first, escalate through official channels if it continues', 'Embarrass publicly', 'Send to principal immediately', 'Ignore all disruptions'], 'correct': 0},
        {'id': 'q3', 'content': 'Classroom rules are most effective when?', 'options': ['Co-created with students, positively worded, consistently enforced', 'Long and comprehensive', 'Posted only on teacher\'s desk', 'Changed frequently'], 'correct': 0},
        {'id': 'q4', 'content': 'Best way to encourage quiet students to participate?', 'options': ['Small group or pair work before whole-class sharing', 'Force them to answer in front of everyone', 'Only call on volunteers', 'Award extra marks for participation'], 'correct': 0},
    ],
    'mfg_process': [
        {'id': 'q1', 'content': 'SOP stands for?', 'options': ['Standard Operating Procedure', 'Safety Output Protocol', 'Standard Output Performance', 'Sequential Operation Plan'], 'correct': 0},
        {'id': 'q2', 'content': 'A production floor checklist is used to?', 'options': ['Ensure each step is completed correctly in sequence', 'Track employee attendance', 'Record production costs', 'Manage inventory levels'], 'correct': 0},
        {'id': 'q3', 'content': '5S in lean manufacturing stands for?', 'options': ['Sort, Set in order, Shine, Standardize, Sustain', 'Safety, Speed, Skill, System, Sustain', 'Sort, Secure, Shine, Scale, Support', 'Schedule, Setup, Shift, System, Sustain'], 'correct': 0},
    ],
    'mfg_machine_op': [
        {'id': 'q1', 'content': 'Before operating a machine at start of shift, first do?', 'options': ['Pre-operation safety check and machine inspection', 'Start immediately and begin production', 'Check production schedule first', 'Wait for supervisor verbal approval'], 'correct': 0},
        {'id': 'q2', 'content': 'Tolerance in machine operation refers to?', 'options': ['Allowable variation from a specified dimension', 'Maximum machine speed', 'Heat resistance of materials', 'Operator experience level'], 'correct': 0},
        {'id': 'q3', 'content': 'If a machine makes unusual noise or vibration?', 'options': ['Stop immediately and report to maintenance', 'Continue if behind on production', 'Increase speed to see if noise changes', 'Wear more ear protection and continue'], 'correct': 0},
        {'id': 'q4', 'content': 'Preventive maintenance (PM) is?', 'options': ['Scheduled maintenance to prevent breakdowns before they occur', 'Maintenance done only after breakdown', 'Daily cleaning routine only', 'Quarterly operator skills check'], 'correct': 0},
    ],
    'mfg_qc': [
        {'id': 'q1', 'content': 'QC vs QA — key difference?', 'options': ['QC detects defects in finished products; QA prevents defects via process control', 'They mean the same thing', 'QA happens after production; QC is planning-focused', 'QC is documentation only'], 'correct': 0},
        {'id': 'q2', 'content': 'A defect in QC is?', 'options': ['Any characteristic that does not conform to specifications', 'Any machine malfunction', 'An employee error only', 'A delayed shipment'], 'correct': 0},
        {'id': 'q3', 'content': 'Six Sigma targets defects at?', 'options': ['3.4 per million opportunities', 'Zero defects only', 'Less than 1% of output', '10 per thousand units'], 'correct': 0},
    ],
    'log_route': [
        {'id': 'q1', 'content': 'Route optimization is?', 'options': ['Finding the most efficient sequence of stops to minimise time/cost/distance', 'The fastest direct route between two points', 'A GPS real-time navigation feature', 'A delivery schedule format'], 'correct': 0},
        {'id': 'q2', 'content': 'Most important factor when prioritising delivery routes?', 'options': ['Delivery time windows and customer priority', 'Driver preference', 'Vehicle type alone', 'Distance alone'], 'correct': 0},
        {'id': 'q3', 'content': 'Two deliveries have conflicting time windows. Best approach?', 'options': ['Contact lower-priority customer to reschedule and confirm', 'Skip the harder delivery', 'Deliver both late without notice', 'Wait for management before acting'], 'correct': 0},
    ],
    'log_safety': [
        {'id': 'q1', 'content': 'Correct manual lifting technique?', 'options': ['Bend knees, straight back, lift with legs, hold load close', 'Bend at waist and lift quickly', 'Always lift alone to save time', 'Only relevant for loads over 25kg'], 'correct': 0},
        {'id': 'q2', 'content': 'When operating a forklift, eyes should be?', 'options': ['In the direction of travel', 'On the load at all times', 'On the speedometer', 'On the dock door'], 'correct': 0},
        {'id': 'q3', 'content': 'Color for emergency stop buttons in a warehouse?', 'options': ['Red', 'Yellow', 'Green', 'Blue'], 'correct': 0},
    ],
    'tel_field_safety': [
        {'id': 'q1', 'content': 'Before climbing a telecom pole, first step?', 'options': ['Hazard assessment and full PPE on', 'Climb immediately and assess from top', 'Work alone to go faster', 'Only check weather'], 'correct': 0},
        {'id': 'q2', 'content': 'Minimum safe distance from energised overhead power lines?', 'options': ['At least 3 metres unless properly de-energised', '1 metre with insulating gloves', 'Only relevant above 100kV', 'No minimum with proper training'], 'correct': 0},
        {'id': 'q3', 'content': 'You discover an unexpected energised line while working. You should?', 'options': ['Stop immediately, move to safe distance, report to supervisor', 'Work carefully around it', 'Cover with insulating tape and continue', 'Finish task then report'], 'correct': 0},
    ],
    'tel_tech_support': [
        {'id': 'q1', 'content': 'Customer reports no internet. Your first troubleshooting step?', 'options': ['Ask them to restart the router and check indicator lights', 'Schedule technician visit immediately', 'Escalate to level 2 support', 'Check for outages in area first'], 'correct': 0},
        {'id': 'q2', 'content': 'Customer\'s internet is slower than their plan speed. Do first?', 'options': ['Ask them to run a speed test and report results', 'Upgrade their plan immediately', 'Arrange router replacement', 'Check physical phone line'], 'correct': 0},
        {'id': 'q3', 'content': 'At start of every tech support call, collect?', 'options': ['Account number, issue description, devices affected', 'Only the issue description', 'Their payment status', 'Service contract details only'], 'correct': 0},
        {'id': 'q4', 'content': 'Customer frustrated after 3 transfers. You begin with?', 'options': ['Acknowledge frustration, assure no further transfers, resolve now', 'Transfer to specialist immediately', 'Ask them to call back off-peak', 'Explain the reason for previous transfers'], 'correct': 0},
    ],
    'fin_rm_simulation': [
        {'id': 'q1', 'content': 'Client has ₹5L for 3 years, moderate risk. Suggest?', 'options': ['Balanced mix of mutual funds and fixed deposits', 'High-risk equity stocks only', 'Savings account only', 'Real estate only'], 'correct': 0},
        {'id': 'q2', 'content': 'Client saving for child\'s education in 10 years. Best product?', 'options': ['Long-term SIP', '1-year fixed deposit', 'Regular savings account', 'Current account'], 'correct': 0},
        {'id': 'q3', 'content': 'Cross-selling in banking means?', 'options': ['Recommending additional relevant products to existing customers', 'Referring customers to competitors', 'Processing cross-border transfers', 'Selling across multiple branches'], 'correct': 0},
    ],
    'fin_integrity': [
        {'id': 'q1', 'content': 'An existing client offers you a personal gift to prioritise their transaction. You?', 'options': ['Politely decline and explain bank gift policy', 'Accept if small amount', 'Report only if asked', 'Accept and disclose later in quarterly report'], 'correct': 0},
        {'id': 'q2', 'content': 'You discover a colleague altering transaction records. You?', 'options': ['Report immediately to compliance officer or ethics hotline', 'Confront the colleague directly first', 'Ignore to avoid conflict', 'Monitor for another week'], 'correct': 0},
        {'id': 'q3', 'content': 'A conflict of interest arises when?', 'options': ['Personal interests interfere with professional duties', 'Two customers apply for same loan', 'Two bank departments disagree on policy', 'Exchange rate fluctuations affect a transaction'], 'correct': 0},
    ],
    'fin_insurance_product': [
        {'id': 'q1', 'content': 'Term vs whole life insurance — key difference?', 'options': ['Term covers fixed period, no cash value; whole life covers lifetime and builds cash value', 'Term is more expensive', 'Whole life pays on specific trigger events only', 'They are identical products'], 'correct': 0},
        {'id': 'q2', 'content': 'In insurance, "premium" is?', 'options': ['Regular payment to maintain coverage', 'Payout received after a claim', 'Type of coverage selected', 'Insurer\'s profit margin'], 'correct': 0},
        {'id': 'q3', 'content': 'Sum assured in life insurance means?', 'options': ['Guaranteed amount paid on death or maturity', 'Total premiums paid over the policy', 'Investment returns generated', 'Hospital bill covered'], 'correct': 0},
        {'id': 'q4', 'content': 'Health insurance co-pay is?', 'options': ['Fixed portion insured pays out of pocket', 'Total hospital bill', 'Bonus for not claiming', 'Insurer\'s profit margin'], 'correct': 0},
    ],
    'retail_etiquette': [
        {'id': 'q1', 'content': 'Most appropriate greeting when a customer enters your store?', 'options': ['Eye contact, smile, warm verbal greeting', 'Wait for them to ask for help', 'Immediately offer a discount', 'Ask what they want before greeting'], 'correct': 0},
        {'id': 'q2', 'content': 'Customer comparing two products. You?', 'options': ['Politely offer to answer any questions about the products', 'Leave them completely alone', 'Tell them which to buy without asking', 'Ask them to decide quickly'], 'correct': 0},
        {'id': 'q3', 'content': 'Professional service etiquette includes?', 'options': ['Neat appearance, polite communication, genuine attentiveness', 'Product knowledge only', 'Speed of service only', 'Strict script adherence only'], 'correct': 0},
    ],
    'retail_pos_knowledge': [
        {'id': 'q1', 'content': 'POS stands for?', 'options': ['Point of Sale', 'Product Order System', 'Purchase Operations Software', 'Payment Operations Station'], 'correct': 0},
        {'id': 'q2', 'content': 'Customer pays ₹500 for a ₹347 item. Correct change?', 'options': ['₹153', '₹147', '₹163', '₹143'], 'correct': 0},
        {'id': 'q3', 'content': 'Card payment is declined. You?', 'options': ['Inform calmly and suggest alternate payment method', 'Retry repeatedly', 'Cancel without informing customer', 'Charge manually'], 'correct': 0},
        {'id': 'q4', 'content': 'Processing a return on POS typically requires?', 'options': ['Original receipt, reason for return, item condition', 'Only customer name', 'Only item barcode', 'Manager approval for all returns'], 'correct': 0},
    ],
    'con_material': [
        {'id': 'q1', 'content': 'Standard water-to-cement ratio for structural concrete?', 'options': ['0.4 to 0.6 depending on required strength', '0.1 to 0.2', '0.8 to 1.0', 'Equal parts water and cement'], 'correct': 0},
        {'id': 'q2', 'content': 'TMT steel is used for?', 'options': ['Reinforcing concrete to resist tensile stress', 'Decorative finishing work', 'Window frames only', 'Foundation insulation'], 'correct': 0},
        {'id': 'q3', 'content': 'Concrete curing is done to?', 'options': ['Maintain moisture for full hydration and strength development', 'Accelerate drying time', 'Add binding agents', 'Seal against rainwater'], 'correct': 0},
        {'id': 'q4', 'content': 'Material for waterproofing flat roofs?', 'options': ['Bituminous membrane or polyurethane waterproofing compound', 'Ordinary cement plaster', 'Sand mortar screed', 'Plain concrete'], 'correct': 0},
    ],
    # FREE / GENERAL PLAN MCQ ASSESSMENTS
    'gen_aptitude': [
        {'id': 'q1',  'content': 'If a train travels 240 km in 3 hours, what is its speed?',                                                          'options': ['80 km/h', '60 km/h', '90 km/h', '75 km/h'],                                   'correct': 0},
        {'id': 'q2',  'content': 'What comes next in the series: 2, 6, 18, 54, ___?',                                                                  'options': ['162', '108', '72', '216'],                                                     'correct': 0},
        {'id': 'q3',  'content': 'If APPLE = 50, each letter is worth its position in alphabet. What is CAT worth?',                                   'options': ['24', '20', '30', '18'],                                                        'correct': 0},
        {'id': 'q4',  'content': 'A shopkeeper buys an item for ₹400 and sells at 25% profit. Selling price?',                                         'options': ['₹500', '₹450', '₹480', '₹525'],                                               'correct': 0},
        {'id': 'q5',  'content': 'All roses are flowers. Some flowers fade quickly. Therefore?',                                                        'options': ['Some roses may fade quickly', 'All roses fade quickly', 'No roses fade', 'Cannot be determined'], 'correct': 0},
        {'id': 'q6',  'content': 'Find the odd one out: 8, 27, 64, 100, 125',                                                                          'options': ['100', '27', '64', '125'],                                                      'correct': 0},
        {'id': 'q7',  'content': 'A is 3 years older than B. B is 2 years younger than C. If C is 20, how old is A?',                                  'options': ['21', '19', '23', '18'],                                                        'correct': 0},
        {'id': 'q8',  'content': 'If 6 workers complete a job in 10 days, how many days for 4 workers?',                                               'options': ['15', '12', '20', '9'],                                                         'correct': 0},
        {'id': 'q9',  'content': 'Mirror image: If LEFT is written in a mirror, it appears as?',                                                       'options': ['TFEL', 'LEFT', 'TLEF', 'EFTL'],                                               'correct': 0},
        {'id': 'q10', 'content': 'Which shape has the most lines of symmetry: equilateral triangle, square, regular hexagon, rectangle?',              'options': ['Regular hexagon', 'Square', 'Rectangle', 'Equilateral triangle'],              'correct': 0},
    ],
    'gen_psychometric': [
        {'id': 'q1',  'content': 'Your team disagrees on an approach. You believe your idea is better. You:',                                          'options': ['Present your case with evidence and invite discussion', 'Insist until they agree', 'Stay quiet to avoid conflict', 'Do it your way without telling anyone'], 'correct': 0},
        {'id': 'q2',  'content': 'You discover a colleague made an error that could affect the project. You:',                                         'options': ['Inform them privately and offer to help fix it', 'Report directly to manager without telling them', 'Ignore it, not your responsibility', 'Fix it yourself and take credit'], 'correct': 0},
        {'id': 'q3',  'content': 'You are given 3 urgent tasks with the same deadline. You:',                                                          'options': ['Prioritise by impact and inform stakeholders of any risk', 'Work on whichever seems easiest first', 'Ask to drop one without discussion', 'Work on all three simultaneously regardless of quality'], 'correct': 0},
        {'id': 'q4',  'content': 'A customer is rude to you on a call. You:',                                                                          'options': ['Stay calm, address their concern professionally', 'Match their energy to assert yourself', 'Hang up the call', 'Transfer immediately without trying to help'], 'correct': 0},
        {'id': 'q5',  'content': 'You make a mistake that causes a delay. You:',                                                                       'options': ['Acknowledge it, explain what happened, and propose a solution', 'Blame external factors', 'Hide it hoping it resolves itself', 'Blame a colleague'], 'correct': 0},
        {'id': 'q6',  'content': 'A new company policy is announced that you disagree with. You:',                                                     'options': ['Follow it while raising concerns through proper channels', 'Ignore the policy', 'Complain to all colleagues', 'Refuse to comply publicly'], 'correct': 0},
        {'id': 'q7',  'content': 'You are asked to train a new joiner who struggles to learn quickly. You:',                                           'options': ['Adjust your approach and be patient; everyone learns differently', 'Report them as incompetent', 'Do their work for them', 'Avoid them as training takes too much time'], 'correct': 0},
        {'id': 'q8',  'content': 'You feel overwhelmed with your workload. You:',                                                                      'options': ['Talk to your manager about reprioritising', 'Work late every night without saying anything', 'Deliver late without any communication', 'Decline all new tasks without explanation'], 'correct': 0},
        {'id': 'q9',  'content': 'Which statement best describes your approach to deadlines?',                                                         'options': ['I plan ahead and flag risks early', 'I work best under last-minute pressure', 'Deadlines are guidelines, not rules', 'I avoid committing to deadlines to avoid failure'], 'correct': 0},
        {'id': 'q10', 'content': 'A colleague takes credit for your idea in a meeting. You:',                                                          'options': ['Calmly clarify your contribution at an appropriate moment', 'Confront them aggressively in the meeting', 'Do nothing and let it go permanently', 'Complain to HR immediately'], 'correct': 0},
    ],
    'gen_attention_detail': [
        {'id': 'q1',  'content': 'Which number is different? 1234, 1234, 1243, 1234, 1234',                                                            'options': ['1243', '1234', 'All are the same', 'Cannot tell'],                             'correct': 0},
        {'id': 'q2',  'content': '17 × 8 = ?',                                                                                                        'options': ['136', '126', '144', '132'],                                                    'correct': 0},
        {'id': 'q3',  'content': 'Spot the error: "The manger reviewed the reports and found no discrepencies."',                                      'options': ['Both "manger" and "discrepencies" are misspelt', 'Only "manger" is wrong', 'Only "discrepencies" is wrong', 'No errors'], 'correct': 0},
        {'id': 'q4',  'content': '144 ÷ 12 + 5 × 3 = ?',                                                                                             'options': ['27', '39', '57', '21'],                                                        'correct': 0},
        {'id': 'q5',  'content': 'Which email address is different? a) john.doe@company.com b) john.doe@company.com c) john.d0e@company.com d) john.doe@company.com', 'options': ['c) john.d0e@company.com', 'a)', 'b)', 'd)'],                    'correct': 0},
        {'id': 'q6',  'content': 'Invoice total: 3 items at ₹150, 2 items at ₹275, 1 item at ₹400. Total?',                                           'options': ['₹1,400', '₹1,350', '₹1,450', '₹1,300'],                                      'correct': 0},
        {'id': 'q7',  'content': 'Count the Fs: "FINISHED FILES ARE THE RESULT OF YEARS OF SCIENTIFIC STUDY COMBINED WITH THE EXPERIENCE OF YEARS"', 'options': ['6', '3', '4', '5'],                                                           'correct': 0},
        {'id': 'q8',  'content': '250 + 75 × 2 − 50 = ? (follow BODMAS)',                                                                            'options': ['400', '600', '300', '550'],                                                    'correct': 0},
        {'id': 'q9',  'content': 'Spot the duplicate in this list: Apple, Banana, Cherry, Banana, Date, Fig',                                         'options': ['Banana', 'Apple', 'Cherry', 'Fig'],                                            'correct': 0},
        {'id': 'q10', 'content': 'A report shows sales of ₹1,20,000 in Q1, ₹95,000 in Q2, ₹1,10,000 in Q3, ₹1,35,000 in Q4. Average quarterly sales?', 'options': ['₹1,15,000', '₹1,10,000', '₹1,05,000', '₹1,20,000'],                       'correct': 0},
    ],
    'gen_interview_prep': [
        {'id': 'q1',  'content': 'The STAR method in interviews stands for?',                                                                          'options': ['Situation, Task, Action, Result', 'Skill, Talent, Attitude, Role', 'Strength, Task, Ability, Result', 'Scenario, Target, Action, Review'], 'correct': 0},
        {'id': 'q2',  'content': '"Tell me about yourself" — best approach?',                                                                          'options': ['Brief professional summary: past experience, current skills, and why you\'re here', 'Share your full life story chronologically', 'List every job you\'ve ever held', 'Talk only about personal hobbies and interests'], 'correct': 0},
        {'id': 'q3',  'content': 'When asked "What is your greatest weakness?", you should:',                                                          'options': ['Mention a real weakness and explain the steps you\'re taking to improve it', 'Say "I have no weaknesses"', 'Give a strength disguised as a weakness (e.g., "I work too hard")', 'Refuse to answer as it may hurt your chances'], 'correct': 0},
        {'id': 'q4',  'content': 'Appropriate attire for a corporate interview in India?',                                                              'options': ['Formal business attire — clean, ironed, and conservative', 'Casual jeans and a t-shirt', 'Anything comfortable', 'Sportswear if the company is a startup'], 'correct': 0},
        {'id': 'q5',  'content': 'You arrive for an interview and are asked to wait 20 minutes past your scheduled time. You:',                        'options': ['Wait patiently and use the time to review your notes', 'Leave immediately as it shows disrespect', 'Complain loudly to the receptionist', 'Repeatedly ask the receptionist for updates every 2 minutes'], 'correct': 0},
        {'id': 'q6',  'content': '"Where do you see yourself in 5 years?" The safest and most effective response focuses on:',                         'options': ['Growth within the company and contribution to the role', 'Getting the interviewer\'s job', 'Starting your own competing business', 'Not knowing and saying so honestly'], 'correct': 0},
        {'id': 'q7',  'content': 'Good body language during an interview includes:',                                                                   'options': ['Firm handshake, upright posture, steady eye contact, and nodding when appropriate', 'Leaning back with arms crossed', 'Looking at your phone between questions', 'Avoiding all eye contact to seem humble'], 'correct': 0},
        {'id': 'q8',  'content': 'At the end of the interview, the best question to ask is:',                                                          'options': ['"What does success look like in this role in the first 90 days?"', '"How much leave do I get?"', '"What is the highest salary you\'ve offered for this role?"', '"Can I work from home every day?"'], 'correct': 0},
        {'id': 'q9',  'content': 'If you do not know the answer to a technical question, you should:',                                                 'options': ['Acknowledge it honestly and explain how you would approach finding the answer', 'Make up a confident-sounding answer', 'Change the subject immediately', 'Say "That\'s not relevant to this job"'], 'correct': 0},
        {'id': 'q10', 'content': 'A thank-you email after an interview should be sent:',                                                               'options': ['Within 24 hours of the interview', 'Only if you want the job badly', 'One week later', 'Never — it looks desperate'], 'correct': 0},
    ],
    'gen_english_prof': [
        {'id': 'q1',  'content': 'Choose the grammatically correct sentence:',                                                                         'options': ['Neither the manager nor the employees were informed.', 'Neither the manager nor the employees was informed.', 'Neither the manager nor the employees is informed.', 'Neither the manager nor the employees are informed.'], 'correct': 0},
        {'id': 'q2',  'content': 'Choose the correct word: "The data ___ clearly showing an upward trend."',                                          'options': ['are', 'is', 'were', 'was'],                                                    'correct': 0},
        {'id': 'q3',  'content': 'What does the idiom "burn the midnight oil" mean?',                                                                  'options': ['Work late into the night', 'Waste resources', 'Start a fire', 'Cause problems'], 'correct': 0},
        {'id': 'q4',  'content': 'Opposite of "verbose"?',                                                                                            'options': ['Concise', 'Wordy', 'Fluent', 'Silent'],                                        'correct': 0},
        {'id': 'q5',  'content': 'Which sentence uses the passive voice?',                                                                             'options': ['The report was submitted by the analyst.', 'The analyst submitted the report.', 'Submit the report immediately.', 'The analyst is submitting the report.'], 'correct': 0},
        {'id': 'q6',  'content': 'What is phishing?',                                                                                                 'options': ['Fraudulent attempt to obtain sensitive information by disguising as a trusted entity', 'A type of firewall', 'A secure login method', 'An email encryption standard'], 'correct': 0},
        {'id': 'q7',  'content': 'A strong password should:',                                                                                         'options': ['Be at least 12 characters with letters, numbers, and symbols', 'Be your name and birth year', 'Be shared with your team for easy access', 'Be reused across accounts for convenience'], 'correct': 0},
        {'id': 'q8',  'content': 'You receive an email from "IT Support" asking for your password urgently. You should:',                              'options': ['Ignore/report it — legitimate IT never asks for passwords via email', 'Reply with your password', 'Forward it to colleagues', 'Click the link to verify your account'], 'correct': 0},
        {'id': 'q9',  'content': 'What does HTTPS in a website URL indicate?',                                                                        'options': ['The connection is encrypted and more secure', 'The website is government-owned', 'The site is free from viruses', 'The website is faster than HTTP'], 'correct': 0},
        {'id': 'q10', 'content': 'Two-Factor Authentication (2FA) means?',                                                                            'options': ['Verifying identity with two separate methods (e.g. password + OTP)', 'Using two different passwords', 'Logging in from two devices simultaneously', 'Having two email accounts'], 'correct': 0},
    ],
}


def get_format_type(assessment_key: str) -> str:
    return ASSESSMENT_FORMAT_MAP.get(assessment_key, 'mcq')


def get_format_description(format_type: str) -> str:
    return FORMAT_DESCRIPTIONS.get(format_type, 'Assessment')


PLATFORM_STARTER_TEMPLATES: Dict[str, str] = {
    'python':     '# Write your Python solution here\n\n\n',
    'javascript': '// Write your JavaScript solution here\n\n\nconsole.log();\n',
    'typescript': '// Write your TypeScript solution here\n\nfunction solve(input: any): any {\n    // Your code here\n}\n\nconsole.log(solve(undefined));\n',
    'java':       'public class Solution {\n    public static void main(String[] args) {\n        // Write your Java solution here\n    }\n}\n',
    'cpp':        '#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your C++ solution here\n    return 0;\n}\n',
    'go':         'package main\n\nimport "fmt"\n\nfunc main() {\n    // Write your Go solution here\n    fmt.Println()\n}\n',
    'sql':        '-- Write your SQL query here\n\nSELECT\n    \nFROM\n    \nWHERE\n    ;\n',
}


def build_sections(assessment_key: str, metadata: dict, ollama_questions: list = None,
                   format_override: str = None, content_override: list = None,
                   ollama_mcq: list = None, platform: str = None,
                   ollama_voice_content: dict = None) -> list:
    fmt = format_override or get_format_type(assessment_key)

    if fmt == 'voice_test':
        raw = VOICE_TEST_FORMATS.get(assessment_key, [])
        vc = ollama_voice_content or {}
        sections = []
        for s in raw:
            sec = dict(s)
            etype = sec.get('exercise_type')
            if sec.get('items') == '__OLLAMA__':
                # qa_verbal: use Ollama questions or fallback
                if vc.get('questions'):
                    sec['items'] = [
                        {'id': f'q{i}', 'content': q}
                        for i, q in enumerate(vc['questions'], 1)
                    ]
                elif ollama_questions:
                    sec['items'] = [
                        {'id': f'q{i}', 'content': q.get('question', q.get('content', str(q)))}
                        for i, q in enumerate(ollama_questions, 1)
                    ]
                else:
                    sec['items'] = [
                        {'id': 'q1', 'content': 'Describe a challenging situation you encountered in a professional context and how you resolved it.'},
                        {'id': 'q2', 'content': 'What are the most important skills for this role and how do you demonstrate them?'},
                        {'id': 'q3', 'content': 'Give an example of when clear communication made a significant difference in your work.'},
                    ]
            elif etype == 'read_aloud' and vc.get('passages'):
                sec['items'] = [
                    {'id': f'p{i}', 'content': p}
                    for i, p in enumerate(vc['passages'], 1)
                ]
            elif etype == 'repeat_sentence' and vc.get('sentences'):
                sec['items'] = [
                    {'id': f'r{i}', 'content': sent}
                    for i, sent in enumerate(vc['sentences'], 1)
                ]
            elif etype == 'topic_speaking' and vc.get('topics'):
                sec['items'] = [
                    {'id': f't{i}', 'content': topic}
                    for i, topic in enumerate(vc['topics'], 1)
                ]
            sections.append(sec)
        return sections

    elif fmt == 'voice_scenario':
        # Ollama-generated scenarios first; fall back to hardcoded, then generic
        items = None
        if ollama_questions:
            items = [
                {'id': f'sc{i}', 'content': q.get('question', str(q)), 'context': 'Scenario'}
                for i, q in enumerate(ollama_questions, 1)
            ]
        if not items:
            items = VOICE_SCENARIO_ITEMS.get(assessment_key) or []
        if not items:
            items = [
                {'id': 'sc1', 'content': 'You are dealing with a challenging situation in your professional role. Describe how you would handle it.', 'context': 'Professional Scenario'},
                {'id': 'sc2', 'content': 'A colleague makes a mistake that affects your work. How do you address this professionally?', 'context': 'Workplace Scenario'},
                {'id': 'sc3', 'content': 'You are under time pressure to deliver a critical task. Describe your approach.', 'context': 'Time Pressure Scenario'},
            ]
        return [{
            'id': 's_scenarios',
            'title': metadata.get('name', 'Scenario Assessment'),
            'instruction': 'Read each scenario carefully, then respond verbally as you would in a real professional situation. You have 90 seconds per scenario.',
            'exercise_type': 'voice_scenario',
            'duration_per_item': 90,
            'items': items,
        }]

    elif fmt == 'text_writing':
        # Ollama-generated prompts first; fall back to hardcoded, then generic
        if ollama_questions:
            return [{
                'id': 's_writing',
                'title': metadata.get('name', 'Writing Assessment'),
                'instruction': 'Write a clear, professional response for each prompt.',
                'exercise_type': 'text_response',
                'format_hint': 'Be specific, well-structured, and use professional language.',
                'duration_per_item': 300,
                'items': [
                    {'id': f'w{i}', 'content': q.get('question', str(q))}
                    for i, q in enumerate(ollama_questions, 1)
                ],
            }]
        hardcoded = TEXT_WRITING_SECTIONS.get(assessment_key)
        if hardcoded:
            return hardcoded
        return [{
            'id': 's_writing',
            'title': metadata.get('name', 'Writing Assessment'),
            'instruction': 'Write a clear, professional response for each prompt.',
            'exercise_type': 'text_response',
            'format_hint': 'Be specific and well-structured.',
            'duration_per_item': 300,
            'items': [{'id': 'w1', 'content': f'Describe your approach to {metadata.get("name", "this subject")} in a professional context. Be specific with examples.'}],
        }]

    elif fmt == 'coding_test':
        problems = None

        # When platform is specified and Ollama produced questions, build structured problems
        if platform and ollama_questions:
            starter = PLATFORM_STARTER_TEMPLATES.get(platform, '# Write your solution here\n')
            problems = [
                {
                    'id': f'p{i}',
                    'content': q.get('question', q.get('content', f'Challenge {i}')),
                    'language': platform,
                    'starter_code': starter,
                }
                for i, q in enumerate(ollama_questions, 1)
            ]

        # Fall back to hardcoded problems (prefer platform-specific key, then generic)
        if not problems:
            platform_key = f"{assessment_key}_{platform}" if platform else assessment_key
            problems = CODING_PROBLEMS.get(platform_key) or CODING_PROBLEMS.get(assessment_key) or []

        # If still empty, generate a generic placeholder
        if not problems:
            lang = platform or ('sql' if 'sql' in assessment_key else
                    'javascript' if ('js' in assessment_key or 'react' in assessment_key) else
                    'text' if 'design' in assessment_key else 'python')
            starter = PLATFORM_STARTER_TEMPLATES.get(lang, '# Write your solution here\n')
            problems = [{'id': 'p1', 'content': f'Solve the {metadata.get("name", "coding")} challenge below. Show your reasoning.', 'language': lang, 'starter_code': starter}]

        # Ensure all problems carry the chosen platform language and starter code
        if platform:
            starter = PLATFORM_STARTER_TEMPLATES.get(platform, problems[0].get('starter_code', '# Write here\n'))
            problems = [{**p, 'language': platform, 'starter_code': p.get('starter_code', starter) if p.get('platform') == platform else starter} for p in problems]

        lang_label = (platform or problems[0].get('language', 'code')).upper()
        return [{
            'id': 's_coding',
            'title': f'{metadata.get("name", "Coding Challenge")} — {lang_label}',
            'instruction': 'Read each problem carefully. Write clean, working code. Add comments to explain your approach.',
            'exercise_type': 'code',
            'duration_per_item': 1800,
            'items': problems,
        }]

    else:  # mcq
        # Prefer Ollama MCQ (with real options); fall back to hardcoded, then generic
        questions = ollama_mcq or MCQ_FALLBACK.get(assessment_key) or []
        if not questions:
            questions = [
                {'id': f'q{i}', 'content': f'Question {i}: Which option best demonstrates knowledge of {metadata.get("name", "this subject")}?',
                 'options': ['Best practice option', 'Incorrect approach', 'Partially correct', 'Unrelated option'], 'correct': 0}
                for i in range(1, metadata.get('questions', 5) + 1)
            ]
        return [{
            'id': 's_mcq',
            'title': metadata.get('name', 'Knowledge Assessment'),
            'instruction': 'Choose the best answer for each question. Only one answer is correct.',
            'exercise_type': 'mcq',
            'duration_per_item': 60,
            'items': questions,
        }]
