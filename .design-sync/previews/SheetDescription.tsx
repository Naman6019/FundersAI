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

export function DescriptionInSheet() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Risk profile</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Risk profile</SheetTitle>
          <SheetDescription>
            This scheme carries very high risk, per the AMC's official risk-o-meter
            disclosure. Past returns do not guarantee future performance.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Close</Button>} />
          <Button>View risk-o-meter</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
