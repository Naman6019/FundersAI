import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
  Button,
} from 'marketmind';

export function OpenRight() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger
        render={<Button variant="outline">Open filters</Button>}
      />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Filter funds</SheetTitle>
          <SheetDescription>
            Narrow the results by category, AMC, and risk grade.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Cancel</Button>} />
          <Button>Apply filters</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
