import unittest
from intent_router import intent,research_brief
class RoutingTests(unittest.TestCase):
 def test_income(self):
  for q in ['City doesnt matter, just get the clients. You should understand that by now.','Give work to the agents and send the proposals to the clients','Find website clients','/income research prospects']:self.assertEqual(intent(q),'income')
 def test_capabilities(self):self.assertEqual(intent('Can you talk to the agents?'),'capabilities')
 def test_negations(self):
  for q in ["Don't find clients",'Do not assign work to agents','Stop finding leads']:self.assertEqual(intent(q),'chat')
 def test_chat(self):
  for q in ['Hi','yes','Explain my pricing options']:self.assertEqual(intent(q),'chat')
 def test_no_send_instruction(self):self.assertNotIn('send the proposals',research_brief('Give work to the agents and send the proposals to the clients'))
if __name__=='__main__':unittest.main()
