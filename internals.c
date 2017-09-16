typedef struct {
    uint8_t something_else[36];
    char *class_id;
    ...
} VBClass;

typedef struct {
    void *base_addr;
    uint8_t something_else[40];
    VBClass *cls;
    uint8_t something_else[88];
    char *caption;
    ...
} VBObject;

vb_runtime() {
    ...
    VBClass *label = malloc(sizeof(VBObject));
    label->id = malloc(9);
    strcpy(label->id, "VB.Label");
    ...
    VBObject *label_a = malloc(sizeof(VBObject));
    label_a->cls = label;
    label_a->caption = malloc(6);
    strcpy(label_a->caption, "Hello");
    ...
    VBObject *label_b = malloc(sizeof(VBObject));
    label_b->cls = label;
    label_b->caption = malloc(6);
    strcpy(label_b->caption, "World");
    ...
}
