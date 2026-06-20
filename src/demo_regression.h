#ifndef UNEZQUAKE_DEMO_REGRESSION_H
#define UNEZQUAKE_DEMO_REGRESSION_H

void DemoRegression_Init(void);
void DemoRegression_Shutdown(void);
void DemoRegression_CaptureFrame(int physics_frame);
void DemoRegression_RecordTempEntity(int type);
void DemoRegression_AutomationFrame(void);

#endif
