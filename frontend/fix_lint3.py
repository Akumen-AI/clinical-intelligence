import os
import re

def rep(filepath, old, new):
    with open(filepath, "r") as f:
        content = f.read()
    content = content.replace(old, new)
    with open(filepath, "w") as f:
        f.write(content)

# PatientDashboardPage.jsx
rep("src/pages/PatientDashboardPage.jsx", "Patient's", "Patient&apos;s")

# PatientQAPage.jsx
rep("src/pages/PatientQAPage.jsx", '"What are the patient\'s active medications?"', '&quot;What are the patient&apos;s active medications?&quot;')
rep("src/pages/PatientQAPage.jsx", '"What were the latest lab results?"', '&quot;What were the latest lab results?&quot;')
rep("src/pages/PatientQAPage.jsx", 'Sources for the AI\'s response', 'Sources for the AI&apos;s response')
rep("src/pages/PatientQAPage.jsx", '"{parsed.text}"', '&quot;{parsed.text}&quot;')

# NaturalLanguageReportPage.jsx
rep("src/pages/NaturalLanguageReportPage.jsx", "LLM's", "LLM&apos;s")

# ReviewFieldCard.jsx
rep("src/components/ReviewFieldCard.jsx", "} catch (err) {\n        \n      }", "} catch (err) {\n        /* do nothing */\n      }")

# ReviewQueuePage.jsx
rep("src/pages/ReviewQueuePage.jsx", "} catch (err) {\n      \n    }", "} catch (err) {\n      /* do nothing */\n    }")

