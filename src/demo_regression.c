/*
 * Opt-in telemetry for deterministic demo regression tests.
 *
 * This file is compiled only with ENABLE_REGRESSION_HOOKS=ON. Production
 * builds therefore contain no telemetry branch or file I/O.
 */

#include "quakedef.h"
#include "demo_regression.h"

static FILE *demo_regression_file;
static unsigned long demo_regression_sample;
#define DEMO_REGRESSION_MAX_EVENTS 64
static int demo_regression_events[DEMO_REGRESSION_MAX_EVENTS];
static int demo_regression_event_count;

typedef enum {
	demo_regression_automation_idle,
	demo_regression_automation_waiting,
	demo_regression_automation_recording
} demo_regression_automation_state_t;

static demo_regression_automation_state_t demo_regression_automation_state;
static int demo_regression_automation_frame;

static void DemoRegression_Stop_f(void)
{
	if (!demo_regression_file) {
		return;
	}

	fputs("{\"type\":\"end\"}\n", demo_regression_file);
	fclose(demo_regression_file);
	demo_regression_file = NULL;
	Com_Printf("Demo regression capture stopped\n");
}

static void DemoRegression_Start_f(void)
{
	const char *path;

	if (Cmd_Argc() != 2) {
		Com_Printf("usage: demo_regression_start <output.jsonl>\n");
		return;
	}

	DemoRegression_Stop_f();
	path = Cmd_Argv(1);
	demo_regression_file = fopen(path, "wb");
	if (!demo_regression_file) {
		Com_Printf("Could not open demo regression output: %s\n", path);
		return;
	}

	demo_regression_sample = 0;
	demo_regression_event_count = 0;
	fputs("{\"type\":\"header\",\"schema\":1}\n", demo_regression_file);
	Com_Printf("Demo regression capture started: %s\n", path);
}

static void DemoRegression_Finish_f(void)
{
	DemoRegression_Stop_f();
	Cbuf_AddText("quit\n");
}

static void DemoRegression_GenerateReference_f(void)
{
	if (demo_regression_automation_state != demo_regression_automation_idle) {
		Com_Printf("Demo regression automation is already running\n");
		return;
	}

	demo_regression_automation_state = demo_regression_automation_waiting;
	demo_regression_automation_frame = 0;
	Cbuf_AddText("cl_independentPhysics 0\ncl_maxfps 77\nmap e1m1\n");
	Com_Printf("Demo regression automation waiting for e1m1\n");
}

void DemoRegression_Init(void)
{
	Cmd_AddCommand("demo_regression_start", DemoRegression_Start_f);
	Cmd_AddCommand("demo_regression_stop", DemoRegression_Stop_f);
	Cmd_AddCommand("demo_regression_finish", DemoRegression_Finish_f);
	Cmd_AddCommand("demo_regression_generate_reference", DemoRegression_GenerateReference_f);
}

void DemoRegression_Shutdown(void)
{
	DemoRegression_Stop_f();
}

void DemoRegression_RecordTempEntity(int type)
{
	if (demo_regression_file && demo_regression_event_count < DEMO_REGRESSION_MAX_EVENTS) {
		demo_regression_events[demo_regression_event_count++] = type;
	}
}

void DemoRegression_AutomationFrame(void)
{
	if (demo_regression_automation_state == demo_regression_automation_waiting) {
		if (cls.state == ca_active && com_serveractive) {
			Cbuf_AddText("recordqwd phase0_shareware_e1m1\n+forward\n");
			demo_regression_automation_state = demo_regression_automation_recording;
			demo_regression_automation_frame = 0;
		}
		return;
	}

	if (demo_regression_automation_state != demo_regression_automation_recording) {
		return;
	}

	++demo_regression_automation_frame;
	switch (demo_regression_automation_frame) {
		case 50:
			Cbuf_AddText("+jump\n");
			break;
		case 60:
			Cbuf_AddText("-jump\n+moveright\n");
			break;
		case 110:
			Cbuf_AddText("+attack\n");
			break;
		case 120:
			Cbuf_AddText("-attack\n+jump\n");
			break;
		case 130:
			Cbuf_AddText("-jump\n");
			break;
		case 180:
			Cbuf_AddText("-moveright\n-forward\n+left\n");
			break;
		case 230:
			Cbuf_AddText("-left\n+forward\n+jump\n");
			break;
		case 240:
			Cbuf_AddText("-jump\n");
			break;
		case 300:
			Cbuf_AddText("-forward\n-moveright\n-left\n-attack\n-jump\nstopqwd\nquit\n");
			demo_regression_automation_state = demo_regression_automation_idle;
			break;
	}
}

void DemoRegression_CaptureFrame(int physics_frame)
{
	const frame_t *frame;
	const usercmd_t *cmd;
	int i;

	if (!demo_regression_file || !cls.demoplayback || cls.state != ca_active) {
		return;
	}

	frame = &cl.frames[cl.validsequence & UPDATE_MASK];
	cmd = &frame->cmd;

	fprintf(demo_regression_file,
		"{\"type\":\"frame\",\"sample\":%lu,\"client_frame\":%d,"
		"\"valid_sequence\":%d,\"demo_time\":%.9g,\"physics_frame\":%s,"
		"\"origin\":[%.9g,%.9g,%.9g],\"velocity\":[%.9g,%.9g,%.9g],"
		"\"angles\":[%.9g,%.9g,%.9g],\"onground\":%s,\"waterlevel\":%d,"
		"\"weapon\":%d,\"weapon_frame\":%d,"
		"\"command\":{\"msec\":%u,\"forward\":%d,\"side\":%d,\"up\":%d,"
		"\"buttons\":%u,\"impulse\":%u,\"attack\":%s,\"jump\":%s},\"events\":[",
		demo_regression_sample++, cls.framecount, cl.validsequence,
		cls.demotime, physics_frame ? "true" : "false",
		cl.simorg[0], cl.simorg[1], cl.simorg[2],
		cl.simvel[0], cl.simvel[1], cl.simvel[2],
		cl.simangles[0], cl.simangles[1], cl.simangles[2],
		cl.onground ? "true" : "false", cl.waterlevel,
		cl.simwep, cl.simwepframe,
		(unsigned int)cmd->msec, cmd->forwardmove, cmd->sidemove, cmd->upmove,
		(unsigned int)cmd->buttons, (unsigned int)cmd->impulse,
		(cmd->buttons & BUTTON_ATTACK) ? "true" : "false",
		(cmd->buttons & BUTTON_JUMP) ? "true" : "false");

	for (i = 0; i < demo_regression_event_count; ++i) {
		fprintf(demo_regression_file, "%s%d", i ? "," : "", demo_regression_events[i]);
	}
	fputs("]}\n", demo_regression_file);
	demo_regression_event_count = 0;
}
